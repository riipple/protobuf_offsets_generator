use std::env;
use std::fs::File;
use std::io::Write;
use std::path::Path;
use crate::common::generate_struct;
use crate::common::write_to_file;
use crate::common::ClassField;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;

#[derive(Clone)]
pub struct ClassField {
    pub name: String,
    pub offset: usize,
    pub field_type: String,
    pub original_type: String,
    pub size: Option<usize>,
}

impl ClassField {
    pub fn new(
        name: String,
        offset: usize,
        field_type: String,
        original_type: String,
        size: Option<usize>,
    ) -> Self {
        Self {
            name,
            offset,
            field_type,
            original_type,
            size,
        }
    }
}

pub fn generate_struct(class_name: &str, fields: Vec<ClassField>) -> String {
    let mut class_str = String::new();

    class_str.push_str(
        "#[repr(C)]\n\
                #[derive(Debug)]\n",
    );
    class_str.push_str(&format!("pub struct {} {{\n", class_name));

    let mut fields = fields.clone();
    fields.sort_by_key(|v| v.offset);
    let mut offsets_iter = fields.into_iter().peekable();
    let mut next_offset_value = 0;
    let mut first = true;

    while let Some(ClassField {
        name,
        offset,
        original_type,
        field_type,
        size,
    }) = offsets_iter.next()
    {
        let prev_offset = offset;
        let (type_name, type_size) = if let Some(ClassField { offset, .. }) = offsets_iter.peek() {
            let diff = offset - prev_offset;

            if let Some(size) = size {
                (field_type, size)
            } else {
                if diff >= 8 {
                    ("*const usize".to_string(), 8)
                } else {
                    match diff {
                        1 => ("u8".to_string(), 1),
                        2 => ("u16".to_string(), 2),
                        4 => ("u32".to_string(), 4),
                        _ => continue, // impossible to hit in theory
                    }
                }
            }
        } else {
            size.map(|s| (field_type, s))
                .unwrap_or(("*const usize".to_string(), 8))
        };

        let gap = offset as isize - next_offset_value as isize;

        let field_str = if offset > 0 && (first || next_offset_value != offset) {
            let pref = if gap > 0 {
                format!("    _unk{}: [u8; {}],\n", offset, gap)
            } else {
                "".to_string()
            };
            format!(
                "{}    pub {}: {}, // type: {}, offset: {:x}, size: {}, prev_pred: {}, gap: {}\n",
                pref, name, type_name, original_type, offset, type_size, next_offset_value, gap
            )
        } else {
            format!(
                "    pub {}: {}, // type: {}, offset: {:x}, size: {}, prev_pred: {}, gap: {}\n",
                name, type_name, original_type, offset, type_size, next_offset_value, gap
            )
        };

        class_str.push_str(&field_str);
        next_offset_value = offset + type_size;
        first = false;
    }

    class_str.push_str("}\n\n");
    class_str
}

pub fn write_to_file(name: &str, content: &str) {
    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join(name);
    let mut f = File::create(&dest_path).unwrap();

    f.write_all(content.as_bytes()).unwrap();
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProtoStruct {
    pub fields: HashMap<String, ProtoField>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProtoField {
    pub offset: usize,
    pub field_type: String,
    pub original_type: String,
    pub size: usize,
}

pub fn gen_protos() {
    println!("cargo:rerun-if-changed=./protobuf_gen/protobufs.json");

    let json_content =
        fs::read_to_string("./protobuf_gen/protobufs.json").expect("Unable to read file");
    let protos: HashMap<String, ProtoStruct> = serde_json::from_str(&json_content).unwrap();

    let mut res = String::new();
    res.push_str("pub mod protobufs {\n");
    for (name, strct) in protos {
        let struct_out = generate_struct(
            &name,
            strct
                .fields
                .iter()
                .map(|(n, f)| {
                    ClassField::new(
                        n.clone(),
                        f.offset,
                        f.field_type.clone(),
                        f.original_type.clone(),
                        Some(f.size),
                    )
                })
                .collect::<Vec<_>>(),
        );
        res.push_str(&struct_out);

        res.push_str(&format!("impl cs2sdk_core::cpp::cpp_base_class::CPPBaseClass<crate::modules::ClientDll> for {} {{ }}\n\n",  
            name
        ));
    }
    res.push_str("}\n");

    write_to_file("protobufs.rs", &res)
}

fn main() {
    gen_protos();
}
