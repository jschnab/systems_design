#ifndef __api__
#define __api__


#include <stdio.h>

#include "io.h"
#include "namespace.h"


void namespace_create(char *, Db *);

void namespace_use(char *, Db *);

void db_close(Db *);

TreeNode *db_get(char *, Db *);

void db_insert(char *, void *, long, Db *);

Db *db_open(char *);


#endif
