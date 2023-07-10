ALLOC_H = alloc.h
ALLOC_C = alloc.c
ALLOC = $(ALLOC_H) $(ALLOC_C)
DEBUG_H = debug.h
IO_H = io.h
IO_C = io.c
IO = $(IO_H) $(IO_C)
LIST_H = linked_list.h
LIST_C = linked_list.c
LIST = $(LIST_H) $(LIST_C)
TREE_H = tree.h
TREE_C = tree.c
TREE = $(TREE_H) $(TREE_C)

kv: $(ALLOC) $(DEBUG_H) $(IO) $(LIST) $(TREE) main.c
	gcc -Wall -o kv $(ALLOC_C) $(IO_C) $(LIST) $(TREE_C) main.c
