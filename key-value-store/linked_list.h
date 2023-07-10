#ifndef __list__
#define __list__


typedef struct listnode {
    void *data;
    struct listnode *next;
} ListNode;


typedef struct list {
    ListNode *head;
    ListNode *tail;
    long n;
} List;


void list_append(List *, void *);

List *list_create();

void list_destroy(List *);

ListNode *lnode_create(void *);

void lnode_destroy(ListNode *);


#endif
