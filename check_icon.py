"""Check icon resources embedded in the EXE"""
import pefile

pe = pefile.PE('dist2/PinPrompt.exe')

# Find RT_GROUP_ICON (id=14 is RT_GROUP_ICON, id=3 is RT_ICON)
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id == 14:  # RT_GROUP_ICON
        print("Found RT_GROUP_ICON:")
        for sub_entry in entry.directory.entries:
            print(f"  Language sub-entry: id={sub_entry.id}")
            for lang_entry in sub_entry.directory.entries:
                data_rva = lang_entry.data.struct.OffsetToData
                size = lang_entry.data.struct.Size
                data = pe.get_data(data_rva, size)
                # Parse GRPICONDIR
                import struct
                reserved, type_, count = struct.unpack('<HHH', data[:6])
                print(f"  Type: {type_}, Icon count: {count}")
                for i in range(count):
                    offset = 6 + i * 14
                    w, h, colors, reserved2, planes, bpp, img_size, img_id = struct.unpack('<BBBBHHIH', data[offset:offset+14])
                    if w == 0: w = 256
                    if h == 0: h = 256
                    print(f"    Icon {i+1}: {w}x{h}, {bpp}bit, size={img_size}bytes, id={img_id}")
    elif entry.id == 3:  # RT_ICON
        print(f"Found RT_ICON: {len(entry.directory.entries)} sub-entries")
        for sub_entry in entry.directory.entries:
            print(f"  Icon ID: {sub_entry.id}")
