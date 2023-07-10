#include <stdio.h>

#include "alloc.h"
#include "linked_list.h"


void list_append(List *list, void *data) {
    ListNode *node = lnode_create(data);
    if (list->tail != NULL) {
        list->tail->next = node;
    }
    else {
        list->head = node;
    }
    list->tail = node;
    list->n++;
}


List *list_create() {
    List *new = (List *) malloc_safe(sizeof(List));
    new->head = NULL;
    new->tail = NULL;
    new->n = 0;
    return new;
}


void list_destroy(List *list) {
    ListNode *head = list->head;
    ListNode *prev;
    while (head != NULL) {
        prev = head;
        head = head->next;
        lnode_destroy(prev);
    }
    free_safe(list);
}


ListNode *lnode_create(void *data) {
    ListNode *new = (ListNode *) malloc_safe(sizeof(ListNode));
    new->data = data;
    new->next = NULL;
    return new;
}


void lnode_destroy(ListNode *node) {
    if (node != NULL) {
        free_safe(node->data);
        node->data = NULL;
        free_safe(node);
    }
}
