#pragma once

#define GET_MAX(a, b) ((a) > (b) ? (a) : (b))
#define GET_MIN(a, b) ((a) < (b) ? (a) : (b))

#define GET_MAX3(a, b, c) GET_MAX(GET_MAX(a, b), c)
#define GET_MAX4(a, b, c, d) GET_MAX(GET_MAX(a, b), GET_MAX(c, d))
#define GET_MAX6(a, b, c, d, e, f) GET_MAX3(a, b, GET_MAX4(c, d, e, f))
#define GET_MIN4(a, b, c, d) GET_MIN(GET_MIN(a, b), GET_MIN(c, d))

typedef struct _List {
	int capacity;  
	int itemSize;
	int size;
	void *items;
} List;

List *ListNew(int capacity, int itemSize);

void ListClear(List *v);

void ListDestroy(List *v);

int ListAdd(List *v, void *item);

int ListRemove(List *v, int idx);

int ListIndexOf(List *v, void *item);

void *ListGet(List *v, int idx);

void OpenIO();

void InitHolidays();

extern char *GetDllPath();

// @return YYYYMMDD
int GetCurDay();

// @return HHmmSS
int GetCurTime();

int IsTradeDay(int y, int m, int d);

int GetLastTradeDay();

int GetTradeDayBetween(int beginDay, int endDay);







