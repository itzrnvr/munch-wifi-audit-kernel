import sys

p = "/root/kernelsu-next/kernel/selinux/sepolicy.c"
src = open(p, newline="").read()

START = """    struct ebitmap *new_type_attr_map_array =
        ksu_kvrealloc(db->type_attr_map_array, value * sizeof(struct ebitmap),
                      (value - 1) * sizeof(struct ebitmap));"""

END = "    db->sym_val_to_name[SYM_TYPES][value - 1] = key;\n"

if "4.19: sym_val_to_name / type_val_to_struct_array" in src:
    print("ALREADY")
    sys.exit(0)

start = src.index(START)
end = src.index(END, start) + len(END)

v419 = """#if (LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0))
""" + src[start:end] + """
#else
    /* 4.19: sym_val_to_name / type_val_to_struct_array / type_attr_map_array
     * are flex_arrays with fixed capacity — rebuild each with one more slot. */
    struct flex_array *new_attr_map, *new_val_to_struct, *new_val_to_name;
    int j;
    struct ebitmap new_eb;

    new_attr_map =
        flex_array_alloc(sizeof(struct ebitmap), value, GFP_KERNEL | __GFP_ZERO);
    new_val_to_struct = flex_array_alloc(sizeof(struct type_datum *), value,
                                         GFP_KERNEL | __GFP_ZERO);
    new_val_to_name =
        flex_array_alloc(sizeof(char *), value, GFP_KERNEL | __GFP_ZERO);
    if (!new_attr_map || !new_val_to_struct || !new_val_to_name) {
        pr_err("add_type: flex_array_alloc failed\\n");
        return false;
    }

    for (j = 0; j < value - 1; ++j) {
        struct ebitmap *src_eb =
            (struct ebitmap *)flex_array_get(db->type_attr_map_array, j);
        if (!src_eb || flex_array_put(new_attr_map, j, src_eb, GFP_KERNEL)) {
            pr_err("add_type: copy attr map failed at %d\\n", j);
            return false;
        }
        if (flex_array_put_ptr(new_val_to_struct, j,
                               flex_array_get_ptr(db->type_val_to_struct_array, j),
                               GFP_KERNEL) ||
            flex_array_put_ptr(new_val_to_name, j,
                               flex_array_get_ptr(db->sym_val_to_name[SYM_TYPES], j),
                               GFP_KERNEL)) {
            pr_err("add_type: copy val arrays failed at %d\\n", j);
            return false;
        }
    }

    ebitmap_init(&new_eb);
    ebitmap_set_bit(&new_eb, value - 1, 1);
    if (flex_array_put(new_attr_map, value - 1, &new_eb, GFP_KERNEL) ||
        flex_array_put_ptr(new_val_to_struct, value - 1, type, GFP_KERNEL) ||
        flex_array_put_ptr(new_val_to_name, value - 1, key, GFP_KERNEL)) {
        pr_err("add_type: init new slots failed\\n");
        return false;
    }

    flex_array_free(db->type_attr_map_array);
    db->type_attr_map_array = new_attr_map;
    flex_array_free(db->type_val_to_struct_array);
    db->type_val_to_struct_array = new_val_to_struct;
    flex_array_free(db->sym_val_to_name[SYM_TYPES]);
    db->sym_val_to_name[SYM_TYPES] = new_val_to_name;
#endif
"""

src = src[:start] + v419 + src[end:]

# add_typeattribute_raw: ebitmap lives inside the flex_array on 4.19
src = src.replace(
    "    struct ebitmap *sattr = &db->type_attr_map_array[type->value - 1];",
    """#if (LINUX_VERSION_CODE < KERNEL_VERSION(5, 6, 0))
    struct ebitmap *sattr =
        (struct ebitmap *)flex_array_get(db->type_attr_map_array, type->value - 1);
#else
    struct ebitmap *sattr = &db->type_attr_map_array[type->value - 1];
#endif""", 1)

open(p, "w", newline="").write(src)
print("PATCHED add_type + add_typeattribute_raw")
