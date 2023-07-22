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
IO_C = io.c
IO = $(IO_H) $(IO_C)
LIST_H = linked_list.h
LIST_C = linked_list.c
LIST = $(LIST_H) $(LIST_C)
NAMESPACE_H = namespace.h
NAMESPACE_C = namespace.c
NAMESPACE = $(NAMESPACE_H) $(NAMESPACE_C)
SET_H = hashset.h
SET_C = hashset.c
SET = $(SET_H) $(SET_C)
SST_H = sst.h
SST_C = sst.c
SST = $(SST_H) $(SST_C)
TREE_H = tree.h
TREE_C = tree.c
TREE = $(TREE_H) $(TREE_C)

kv: $(ALLOC) $(API) $(DEBUG_H) $(INDEX) $(IO) $(LIST) $(NAMESPACE) $(SET) $(SST) $(TREE) main.c
	gcc -Wall -DNDEBUG -o kv $(ALLOC_C) $(API_C) $(INDEX_C) $(IO_C) $(LIST_C) $(NAMESPACE_C) $(SET_C) $(SST_C) $(TREE_C) main.c -lm
