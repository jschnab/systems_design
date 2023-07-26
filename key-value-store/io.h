#ifndef __io__
#define __io__


#define ATTR_SIZE(Struct, Attribute) sizeof(((Struct*)0)->Attribute)

#define _VERSION "0.1.0\0\0\0"

/* Segment file header offsets. */
#define VER_OFFSET 0
#define VER_SZ 8
#define NUM_REC_OFFSET (VER_OFFSET + VER_SZ)
#define NUM_REC_SZ 8
#define DATA_START_OFFSET (NUM_REC_OFFSET + NUM_REC_SZ)
#define DATA_START_SZ 8
#define INDEX_OFFSET (DATA_START_OFFSET + DATA_START_SZ)

#define MAX_SEG_SZ 1000000

/* Record offsets.  */
#define RECORD_LEN_SZ 4
#define KEY_LEN_SZ 1
#define KEY_MAX_LEN 256
#define RECORD_CST_SZ (RECORD_LEN_SZ + KEY_LEN_SZ)

/* Index region offsets (relative to the start of the index region). */
#define INDEX_LEN_SZ 4
#define INDEX_ITEMS_OFFSET (INDEX_OFFSET + INDEX_LEN_SZ)
#define RECORD_OFFSET_SZ 8
#define INDEX_INTERVAL 100
#define INDEX_ITEM_CST_SZ (2 * (KEY_LEN_SZ + RECORD_OFFSET_SZ))
#define INDEX_ITEM_MAX_SZ (INDEX_ITEM_CST_SZ + 2 * KEY_MAX_LEN)


#endif
