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
MEMTAB_H = memtab.h
MEMTAB_C = memtab.c
MEMTAB = $(MEMTAB_H) $(MEMTAB_C)
TABLE_H = table.h
TABLE_C = table.c
TABLE = $(TABLE_H) $(TABLE_C)
SET_H = hashset.h
SET_C = hashset.c
SET = $(SET_H) $(SET_C)
SEG_H = segment.h
SEG_C = segment.c
SEG = $(SEG_H) $(SEG_C)
WAL_H = wal.h
WAL_C = wal.c
WAL = $(WAL_H) $(WAL_C)

kv: $(ALLOC) $(API) $(DEBUG_H) $(INDEX) $(IO_H) $(LIST) $(MEMTAB) $(TABLE) $(SET) $(SEG) $(WAL) main.c
	gcc -Wall -O3 -o kv $(ALLOC_C) $(API_C) $(INDEX_C) $(LIST_C) $(MEMTAB) $(TABLE_C) $(SET_C) $(SEG_C) $(WAL_C) main.c -lm

timing: $(ALLOC) $(API) $(DEBUG_H) $(INDEX) $(IO_H) $(LIST) $(TABLE) $(SET) $(SEG) $(WAL) timing.c
	gcc -Wall -O3 -DNDEBUG -o timing $(ALLOC_C) $(API_C) $(INDEX_C) $(LIST_C) $(MEMTAB) $(TABLE_C) $(SET_C) $(SEG_C) $(WAL_C) timing.c -lm


timing_search: $(ALLOC) $(API) $(DEBUG_H) $(INDEX) $(IO_H) $(LIST) $(TABLE) $(SET) $(SEG) $(WAL) timing_search.c
	gcc -Wall -O3 -DNDEBUG -o timing_search $(ALLOC_C) $(API_C) $(INDEX_C) $(LIST_C) $(MEMTAB) $(TABLE_C) $(SET_C) $(SEG_C) $(WAL_C) timing_search.c -lm
