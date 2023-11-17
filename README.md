## Protobuf layout generator

Generates cpp class fields offsets for protobufs. They can be used later to generated struct with exactly the same memory layout.

The basic outline of method is to use protoc to generate cpp files, compile, parse pdb to get class layout with offsets, use this information to generate structs.

See `build.rs` for the example of how it can be used to generate rust structs.

To use: paste protobufs into `protobufs.proto` and run: `python launch.py`

Offsets will be in `protobufs.json`

![Neko hacker <3](https://embed.pixiv.net/artwork.php?illust_id=90764693)