/* Replace "dll.h" with the name of your header */
#include "dll.h"
#include <windows.h>
#include <stdio.h>
#include "comm.h"
#include "sqlite/sqlite3.h"
#define _MAX(a, b) (a > b ? a : b)
#define _ABS(a) (a > 0 ? a : -a)

sqlite3 *db;
sqlite3_stmt *stmt2, *stmtacc;

enum ID_PARAM {
	IP_CODE, IP_CDD, IP_DD, IP_ZD, IP_XD, IP_JME, IP_CJJE, IP_NUM
};

struct HGT {
	int day;
	int jme;
	int mrje, mcje, cjje;
};

struct HGT_ACC {
	int day;
	int zj;
	int cgsl; // 持股数量
	float per; // 持股占比
};

const int MAXDAYS_LEN = 20000;

int params[IP_NUM];
int days[MAXDAYS_LEN];
int daysLen;
int zjMax;
HGT hgt[MAXDAYS_LEN];
int hgtLen;
bool isZS; // zhi shu ?

HGT_ACC hgtAcc[MAXDAYS_LEN];
int hgtAccLen;

BOOL needQuery;

void InitMysql() {
// 	OpenIO();
	if (stmt2 != 0 && stmtacc != 0)
		return;
	int status = sqlite3_open("D:/vscode/GP/db/HGT.db", &db);
	if (status != SQLITE_OK) {
		printf("Open HGT sqlite db Fail %d \n", status);
	}
	status = sqlite3_prepare_v2(db, "select day, jme, mrje, mcje , cjje from hgt where code = ? order by day asc", -1, &stmt2, NULL);
	status = sqlite3_prepare_v2(db, "select day, zj, cgsl, per from hgtacc where code = ? order by day asc", -1, &stmtacc, NULL);
	printf("stmt2= %p  stmtcc=%p \n", stmt2, stmtacc);
}

void InitZJParam(int id, int val) {
	if (id == IP_CODE) {
		needQuery = val != params[id];
		if (needQuery) zjMax = 0;
	}
	params[id] = val;
	//printf("InitZJParam id=%d  val=%d \n", id, val);
}

void InitZJParamDate(float* ds, int len) {
	int DL = sizeof(days)/sizeof(int);
	int ml = len < DL ? len : DL;
	for (int i = 0; i < ml; ++i) {
		days[i] = (int)ds[len - ml + i] + 19000000;
	}
	daysLen = ml;
	//printf("InitZJParamDate date=[%d - %d] len:%d \n", (int)ds[0], (int)ds[len-1], len);
	//printf("     days=[%d - %d] len:%d \n", days[0], days[daysLen-1], daysLen);
}

void QueryResult() {
	InitMysql();
	//printf("QueryResult IN need:%d stmt=%p \n", needQuery, stmt);
	if (! needQuery)
		return;
	hgtLen = 0;
	hgtAccLen = 0;
	if (stmt2 == 0 || stmtacc == 0)
		return;
	char code[8];
	sprintf(code, "%06d", params[IP_CODE]);
	isZS = (params[IP_CODE] == 999999) || (params[IP_CODE] == 399001) || (params[IP_CODE] == 399006);
	if (isZS) {
		strcpy(code, "HGTALL");
	}
	memset(hgt, 0, sizeof hgt);
	memset(hgtAcc, 0, sizeof(hgtAcc));

	sqlite3_reset(stmt2);
	sqlite3_clear_bindings(stmt2);
	sqlite3_bind_text(stmt2, 1, code, strlen(code), SQLITE_STATIC);
	// ;
	
	while (sqlite3_step(stmt2) == SQLITE_ROW) {
		HGT *p = &hgt[hgtLen];
		p->day = sqlite3_column_int(stmt2, 0);
		p->jme = sqlite3_column_int(stmt2, 1);
		p->mrje = sqlite3_column_int(stmt2, 2);
		p->mcje = sqlite3_column_int(stmt2, 3);
		p->cjje = sqlite3_column_int(stmt2, 4);
		++hgtLen;
	}

	sqlite3_reset(stmtacc);
	sqlite3_clear_bindings(stmtacc);
	sqlite3_bind_text(stmtacc, 1, code, strlen(code), SQLITE_STATIC);

	while (true)
	{
		int status = sqlite3_step(stmtacc);
		if (status != SQLITE_ROW) {
			break;
		}
		HGT_ACC *p = &hgtAcc[hgtAccLen];
		p->day = sqlite3_column_int(stmtacc, 0);
		p->zj = sqlite3_column_int(stmtacc, 1);
		p->cgsl = sqlite3_column_int(stmtacc, 2);
		p->per = (float)sqlite3_column_double(stmtacc,30);
		++hgtAccLen;
	}
	printf("query hgtAccLen=%d hgtLen=%d \n", hgtAcc, hgtLen);
}

inline int FindDay(int day, int from) {
	for (int i = from; i < daysLen; ++i) {
		if (days[i] == day)
			return i;
		if (days[i] > day) {
			return -1;
		}
	}
	return -1;
}

void CalcHgtZJ(float *out, int len) {
	QueryResult();
	memset(out, 0, sizeof(float) * len);
	int begin = len - daysLen;
	int from = 0;
	for (int i = 0; i < hgtLen; ++i) {
		HGT *p = &hgt[i];
		int j = FindDay(p->day, from);
		if (j == -1) {
			//out[begin + j] = 0;
			continue;
		}
		from = j + 1;
		out[begin + j] = isZS ? p->jme : (float)p->jme / 10000;
		//printf("day = %d out[%d]=%d \n", p->day, j+begin, (int)out[begin + j]);
	}
	//for (int i = 0; i < begin; ++i) out[i] = 0;
}

void CalcHgtZJAbs(float *out, int len) {
	CalcHgtZJ(out, len);
	for (int i = 0; i < len; ++i) {
		if (out[i] < 0) out[i] = -out[i];
	}
}

void CalcHgtCJJE(float *out, int len) {
	QueryResult();
	memset(out, 0, sizeof(float) * len);
	int begin = len - daysLen;
	int from = 0;
	for (int i = 0; i < hgtLen; ++i) {
		HGT *p = &hgt[i];
		int j = FindDay(p->day, from);
		if (j == -1) {
			//out[begin + j] = 0;
			continue;
		}
		from = j + 1;
		out[begin + j] = isZS ? p->cjje : (float)p->cjje / 10000;
		//printf("day = %d out[%d]=%d \n", p->day, j+begin, (int)out[begin + j]);
	}
	//for (int i = 0; i < begin; ++i) out[i] = 0;
}

void GetZJMax(float *out, int len) {
	out[len - 1] = zjMax;
}

void GetThbjPM(int code, float *out, int len) {
	/*
	static Statement *stmt;
	InitMysql();

	out[len - 1] = out[len - 2] = out[len - 3] = out[len - 4] = 0;
	
	if (stmt == NULL) {
		stmt = db.prepare("select day, _jrl_pm from _thbj where _code = ? order by day asc ");
		if (stmt == NULL) {
			return;
		}
		stmt->setBindCapacity(48, 256);
	}
	char scode[8];
	sprintf(scode, "%06d", code);
	stmt->reset();
	stmt->setStringParam(0, scode);
	stmt->bindParams();
	stmt->setResult(0, Statement::CT_INT);
	stmt->setResult(1, Statement::CT_INT);
	stmt->bindResult();
	stmt->exec();
	stmt->storeResult();
	int rc = stmt->getRowsCount();
	out[len - 1] = rc;
	int i = 1;
	while (stmt->fetch()) {
		int pm = stmt->getInt(1);
		out[len - 1 - i] = pm;
		++i;
	}
	*/
}

void GetThNum( int code, float *out, int len ) {
	/*
	static Statement *stmt1, *stmt2;
	InitMysql();

	out[len - 1] = out[len - 2] = out[len - 3] = out[len - 4] = 0;
	if (stmt1 == NULL) {
		stmt1 = db.prepare("select _hy from _base where _code = ? ");
		if (stmt1 == NULL) {
			return;
		}
		stmt1->setBindCapacity(48, 256);
	}
	if (stmt2 == NULL) {
		stmt2 = db.prepare("select count(*) from _base where _hy = ? ");
		if (stmt2 == NULL) {
			return;
		}
		stmt2->setBindCapacity(256, 256);
	}
	char scode[8];
	sprintf(scode, "%06d", code);
	stmt1->reset();
	stmt2->reset();

	stmt1->setStringParam(0, scode);
	stmt1->bindParams();
	stmt1->setResult(0, Statement::CT_STRING, 125);
	stmt1->bindResult();
	stmt1->exec();
	stmt1->storeResult();

	if (! stmt1->fetch()) {
		printf("GetThNum  B2--Error:%s-\n", stmt1->getError());
		return;
	}

	char *hy = stmt1->getString(0);
	if (hy == NULL || strlen(hy) == 0) {
		return;
	}

	stmt2->setStringParam(0, hy);
	stmt2->bindParams();
	stmt2->setResult(0, Statement::CT_INT);
	stmt2->bindResult();
	stmt2->exec();
	stmt2->storeResult();
	if (! stmt2->fetch()) {
		return;
	}
	int num = stmt2->getInt(0);
	out[len - 1] = num;
	*/
}

void CalcHgtAccZJ(float *out, int len) {
	QueryResult();
	memset(out, 0, sizeof(float) * len);
	int begin = len - daysLen;
	int from = 0;
	for (int i = 0; i < hgtAccLen; ++i) {
		HGT_ACC *p = &hgtAcc[i];
		int j = FindDay(p->day, from);
		if (j == -1) {
			//out[begin + j] = 0;
			continue;
		}
		from = j + 1;
		out[begin + j] = (float)p->zj / 10000;
		//printf("day = %d out[%d]=%d \n", p->day, j+begin, (int)out[begin + j]);
	}
}

static int GetHgtAccCgslBase() {
	int minCgsl = 0x7ffffff;
	for (int i = 0; i < hgtAccLen; ++i) {
		HGT_ACC *p = &hgtAcc[i];
		if (p->cgsl > 0 && minCgsl > p->cgsl)
			minCgsl = p->cgsl;
	}
	if (minCgsl == 0x7ffffff) {
		minCgsl = 0;
	}
	return minCgsl / 1000 * 1000;
}

void GetHgtAccCgsl(float *out, int len) {
	QueryResult();
	memset(out, 0, sizeof(float) * len);
	int baseCgsl = GetHgtAccCgslBase();
	int begin = len - daysLen;
	int from = 0;
	for (int i = 0; i < hgtAccLen; ++i) {
		HGT_ACC *p = &hgtAcc[i];
		int j = FindDay(p->day, from);
		if (j == -1) {
			continue;
		}
		from = j + 1;
		if (p->cgsl > 0) {
			out[begin + j] = p->cgsl - baseCgsl;
		}
	}
}

void GetHgtAccPer(float *out, int len) {
	QueryResult();
	memset(out, 0, sizeof(float) * len);
	int begin = len - daysLen;
	int from = 0;
	for (int i = 0; i < hgtAccLen; ++i) {
		HGT_ACC *p = &hgtAcc[i];
		int j = FindDay(p->day, from);
		if (j == -1) {
			continue;
		}
		from = j + 1;
		out[begin + j] = p->per;
	}
}

void CalcCaoDie(float *out, int len, float *bbi, float *downBoll) {
	
}

void GetJGD(int len, float *out, float *code, float *b, float *c)
{
	// OpenIO();
	/**
		static Statement *jgdStmt = NULL;
	InitMysql();
	memset(out, 0, sizeof(float) * len);
	if (jgdStmt == NULL) {
		jgdStmt = db.prepare("select day, _bs, _price from jgd where _code = ? order by day desc");
		jgdStmt->setBindCapacity(48, 256);
	}
	char scode[8] = {0};
	float icode = *code;
	sprintf(scode, "%06d", int(*code));
	printf("code = %s  \n", scode);

	jgdStmt->reset();
	jgdStmt->setStringParam(0, scode);
	jgdStmt->bindParams();
	jgdStmt->setResult(0, Statement::CT_INT, 4);
	jgdStmt->setResult(1, Statement::CT_STRING, 8);
	jgdStmt->setResult(2, Statement::CT_DOUBLE, 8);
	jgdStmt->bindResult();
	jgdStmt->exec();
	jgdStmt->storeResult();

	int idx = 0;
	while (jgdStmt->fetch())
	{
		float day = (float)jgdStmt->getInt(0);
		char bs = *jgdStmt->getString(1);
		float fBS = 0;
		float price = (float)jgdStmt->getDouble(2);

		if (bs == 'b' || bs == 'B')
		{
			fBS = 1;
		}
		else if (bs == 'S' || bs == 's')
		{
			fBS = 2;
		}

		out[len - 1 - idx] = day;
		out[len - 2 - idx] = fBS;
		out[len - 3 - idx] = price;

		printf("%f %f %f \n", day, fBS, price);
		idx += 3;
	}
	*/
}