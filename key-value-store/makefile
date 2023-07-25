ALLOC_H = alloc.h
ALLOC_C = alloc.c
ALLOC = $(ALLOC_H) $(ALLOC_C)
API_H = api.h
API_C = api.c
API = $(API_H) $(API_C)
DEBUG_H = debug.h
INDEX_H = index.h
INDEX_C = index.c
INDEX = $(INDEX_H) $(INDEX_C)
IO_H = io.h
LIST_H = linked_list.h
LIST_C = linked_list.c
LIST = $(LIST_H) $(LIST_C)
TABLE_H = table.h
TABLE_C = table.c
TABLE = $(TABLE_H) $(TABLE_C)
SET_H = hashset.h
SET_C = hashset.c
SET = $(SET_H) $(SET_C)
SST_H = sst.h
SST_C = sst.c
SST = $(SST_H) $(SST_C)
TREE_H = tree.h
TREE_C = tree.c
TREE = $(TREE_H) $(TREE_C)
WAL_H = wal.h
WAL_C = wal.c
WAL = $(WAL_H) $(WAL_C)

kv: $(ALLOC) $(API) $(DEBUG_H) $(INDEX) $(IO_H) $(LIST) $(TABLE) $(SET) $(SST) $(TREE) $(WAL) main.c
	gcc -Wall -o kv $(ALLOC_C) $(API_C) $(INDEX_C) $(LIST_C) $(TABLE_C) $(SET_C) $(SST_C) $(TREE_C) $(WAL_C) main.c -lm
