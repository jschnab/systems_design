#include <stdio.h>

#include "alloc.h"
#include "debug.h"
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


void list_append_left(List *list, void *data) {
    ListNode *node = lnode_create(data);
    if (list->head != NULL) {
        node->next = list->head;
    }
    else {
        list->tail = node;
    }
    list->head = node;
    list->n++;
}


List *list_create() {
    List *new = (List *) malloc_safe(sizeof(List));
    new->head = NULL;
    new->tail = NULL;
    new->n = 0;
    return new;
}


/* Deletes a node at a given index. If the index is greater than the list
 * length, no node is deleted. */
void list_delete(List *list, int index) {
    ListNode *prev = NULL;
    ListNode *cur = list->head;
    while (cur != NULL && index-- > 0) {
        prev = cur;
        cur = cur->next;
    }
    if (cur != NULL) {
        if (prev != NULL) {
            prev->next = cur->next;
        }
        else {
            list->head = cur->next;
        }
        if (cur == list->tail) {
            list->tail = prev;
        }
        free_safe(cur);
        list->n--;
    }
}


void list_destroy(List *list) {
    if (list != NULL) {
        ListNode *head = list->head;
        ListNode *prev;
        while (head != NULL) {
            prev = head;
            head = head->next;
            lnode_destroy(prev);
        }
        free_safe(list);
    }
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
