import os
import re
import json

# Assuming 64-bit pointers
ctype_msvc = {
    "T_32PINT4": {"type": "*const i32", "size": 8},
    "T_32PRCHAR": {"type": "*const u8", "size": 8},
    "T_32PUCHAR": {"type": "*const u8", "size": 8},
    "T_32PULONG": {"type": "*const u32", "size": 8},
    "T_32PLONG": {"type": "*const i32", "size": 8},
    "T_32PUQUAD": {"type": "*const u64", "size": 8},
    "T_32PUSHORT": {"type": "*const u16", "size": 8},
    "T_32PVOID": {"type": "*const usize", "size": 8},  
    "T_64PVOID": {"type": "*const usize", "size": 8},
    "T_INT4": {"type": "i32", "size": 4},
    "T_INT8": {"type": "i64", "size": 8},
    "T_LONG": {"type": "i32", "size": 4},
    "T_QUAD": {"type": "i64", "size": 8},
    "T_RCHAR": {"type": "u8", "size": 1},
    "T_REAL32": {"type": "f32", "size": 4},
    "T_REAL64": {"type": "f64", "size": 8},
    "T_REAL80": {"type": "()", "size": 10}, 
    "T_SHORT": {"type": "i16", "size": 2},
    "T_UCHAR": {"type": "u8", "size": 1},
    "T_UINT4": {"type": "u32", "size": 4},
    "T_ULONG": {"type": "u32", "size": 4},
    "T_UQUAD": {"type": "u64", "size": 8},
    "T_USHORT": {"type": "u16", "size": 2},
    "T_WCHAR": {"type": "u16", "size": 2},
    "T_VOID": {"type": "()", "size": 0}, 
    "T_BOOL08": {"type": "bool", "size": 1},
}

regex = r"""0x([0-9A-Fa-f]+)\s*:\s*Length = ([\d]+).*?LF_FIELDLIST\s*(?:list\[\d+\]\s*=\s*(?:LF_MEMBER|LF_ONEMETHOD),\s*(?:public|private),.*?,\s*(?:type\s*=\s*(0x[0-9A-Fa-f]+),\s*)?offset\s*=\s*(\d+).*?\s*member\s*name\s*=\s*'([^']+)'.*?\s*)*"""
field_regex = r"""list\[(\d+)\]\s*=\s*(?:LF_MEMBER|LF_ONEMETHOD),\s*public,\s*type\s*=\s*(0x[0-9A-Fa-f]+|\w+\(\d+\)),\s*offset\s*=\s*(\d+).*?\s*member\s*name\s*=\s*'([^']+)'.*?\s*"""

class_regex = r"""0x([0-9A-Fa-f]+)\s*:\s*Length\s*=\s*(\d+),\s*Leaf\s*=\s*0x[0-9A-Fa-f]+\s*(LF_STRUCTURE|LF_CLASS)\s*\# members\s*=\s*\d+,\s*field\s*list\s*type\s*0x([0-9A-Fa-f]+),.*\n.*\n.*Size\s*=\s*\d+,\s*class\s*name\s*=\s*([^,]+)"""#r"""0x([0-9A-Fa-f]+)\s*:\s*Length\s*=\s*(\d+),\s*Leaf\s*=.*\n.*\n.*\n.*class\s*name\s*=\s*([^\s,]+)"""
pointers_regex = r"""0x([0-9A-Fa-f]+)\s*:\s*Length\s*=\s*\d+,\s*Leaf\s*=\s*0x[0-9A-Fa-f]+\s*LF_POINTER\s*.*\n.*\n.*Element\s*type\s*:\s*0x([0-9A-Fa-f]+)"""

generic_regex = r"<([^>]+)>"

def parse_data(file_path):
    try:
        with open(file_path, 'r') as file:
            data = file.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        return {}

    impls, types, pointers, result = {}, {}, {}, {}

    for class_match in re.finditer(class_regex, data):
        class_size, class_name = int(class_match.group(2)), class_match.group(5)
        class_id = int("0x" + class_match.group(4), 16)
        types[int("0x" + class_match.group(1), 16)] = {
            "size": class_size, "name": class_name, "fields": class_match.group(4)
        }

        if class_name.endswith("::Impl_"):
            impls[class_id] = {"size": class_size, "name": class_name}

    for class_match in re.finditer(pointers_regex, data):
        pointers[int("0x" + class_match.group(1), 16)] = int("0x" + class_match.group(2), 16)

    for struct_match in re.finditer(regex, data):
        struct_number = int("0x" + struct_match.group(1), 16)
        if struct_number not in impls:
            continue

        struct_start, struct_end = struct_match.start(), struct_match.end()
        field_text = data[struct_start:struct_end]
        field_details = re.findall(field_regex, field_text)
        fields = process_fields(field_details, types, pointers)

        impl_name = impls[struct_number]["name"]
        if not impl_name.startswith("google::protobuf::"):
            result[impl_name.replace("::Impl_", "")] = {"fields": fields}

    return result

def process_fields(field_details, types, pointers):
    fields = {}
    for index, tp, offset, name in field_details:
        if name.startswith("_"):
            continue
        if name.endswith("_"):
            name = name[:-1]

        info = get_type_info(tp, types, pointers)
        fields[name] = {"offset": int(offset) + 0x10, "field_type": info[1], "original_type": str(info[0]), "size": info[2]}
    return fields


def get_type_info(tp, types, pointers):
    # Check if tp is a hex string and can be converted to an int
    if is_hex_string(tp):
        tp_id = int(tp, 16)

        # Handle protobuf built-in types
        tp_name = types.get(int(tp, 16), {}).get("name", "")
        if tp_name.startswith("google::protobuf::RepeatedPtrField"):
            mtch = re.search(generic_regex, tp_name)
            if mtch:
                tp = mtch.group(1)
                return (tp_name, f"cs2sdk_core::protobufs::ProtobufArrayInline<{tp}>", 16)
        if tp_name.startswith("google::protobuf::internal::ArenaStringPtr"):
            return (tp_name, "*mut cs2sdk_core::protobufs::ProtobufString", 8)

        if tp_id in types:
            return (types[tp_id]["name"], types[tp_id]["name"], types[tp_id]["size"])
        if tp_id in pointers:
            p_id = pointers[tp_id]
            return (p_id, "*mut " + types.get(p_id, {"name": "not found"})["name"], 8)

    # Check for MVSC built-in type
    if tp.endswith(")"):
        tp_name_prim = tp.split("(")[0]
        if tp_name_prim in ctype_msvc:
            msvs = ctype_msvc[tp_name_prim]
            return (tp, msvs["type"], msvs["size"])

    # Default return type
    return (tp, "*mut usize", 8)

def is_hex_string(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

os.system('cvdump.exe ./build/Debug/protobuf_gen.pdb >> out.txt')
file_path = 'out.txt'
#parsed_json = parse_pdb_dump(file_path)
parsed_json = parse_data(file_path)

json_object = json.dumps(parsed_json, indent=4)
 
with open("protobufs.json", "w") as outfile:
    outfile.write(json_object)