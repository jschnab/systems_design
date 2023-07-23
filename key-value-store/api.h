#ifndef __api__
#define __api__


#include <stdio.h>

#include "io.h"
#include "table.h"


void use(char *, Db *);

void close(Db *);

void db_delete(char *, Db *);

TreeNode *get(char *, Db *);

void put(char *, void *, long, Db *);

Db *connect(char *);


#endif
