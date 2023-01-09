/* Replace "dll.h" with the name of your header */
#include "dll.h"
#include "comm.h"
#include "hgt.h"
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char DLL_PATH[500];
CRITICAL_SECTION commMutex;

char *GetDllPath() {
	return DLL_PATH;
}

void BeginLock_REF(int len, float* out, float* a, float* b, float* c) {
	EnterCriticalSection(&commMutex);
}

void EndLock_REF(int len, float* out, float* a, float* b, float* c) {
	LeaveCriticalSection(&commMutex);
}

//-----------------------------------------------------------------------------
// �ʽ�
void TdxZJ_REF(int len, float* out, float* ids, float* vals, float *c) {
	// OpenIO();
	int id = (int)ids[0];
	if (id <= 6) {
		int v = (int)vals[0];
		InitZJParam(id, (int)vals[0]);
	} else if (id == 9) {
		InitZJParamDate(vals, len);
	} else if (id == 12) {
		GetZJMax(out, len);
	} else if (id == 13) {
	} else if (id == 20) {
		CalcHgtZJ(out, len);
	} else if (id == 21) {
		CalcHgtZJAbs(out, len);
	} else if (id == 30) {
		CalcHgtCJJE(out, len);
	} else if (id == 40) {
		CalcHgtAccZJ(out, len);
	} else if (id == 60) {
		GetHgtAccCgsl(out, len);
	} else if (id == 70) {
		GetHgtAccPer(out, len);
	}
}

void STRING_REF(int len, float* out, float* code, float* b, float* c) {
	//OpenIO();
	for (int i = 0; i < len; ++i) out[i] = code[i];
}

void THBJ_PM_REF(int len, float* out, float* ids, float* code, float* c) {
	// OpenIO();
	GetThbjPM((int)code[len - 1], out, len);
}

void TH_NUM_REF(int len, float* out, float* ids, float* code, float* c) {
	// OpenIO();
	GetThNum((int)code[len - 1], out, len);
}

static FILE *file = NULL;
void TH_DOWNLOAD_REF(int len, float *out, float *fcmd, float *val, float *ftype)
{
	static void *buffers[50] = {NULL};
	const size_t BUFF_SIZE = 300 * 50 * (4 * 16);
	static int itemNum = 0;
	static int maxCmd = 0;

	OpenIO();
	for (int i = 0; i < sizeof(buffers) / sizeof(void *); ++i)
	{
		if (buffers[i] == NULL) {
			buffers[i] = malloc(BUFF_SIZE);
		}
	}
	
	int cmd = (int)fcmd[0];
	int type = (int)ftype[0]; // 1: int 2:float
	if (cmd >= 0 && cmd < 100 && maxCmd < cmd) {
		maxCmd = cmd;
	}
	if (cmd == 1000)
	{
		int code = (int)val[0];
		// begin
		char path[512];
		int zq = (int)ftype[0];
		sprintf(path, "%s%06d-%d", DLL_PATH, code, zq);
		printf("open data file: %s \n", path);
		file = fopen(path, "wb");
		itemNum = 0;
		return;
	}
	if (file == NULL) {
		return;
	}
	if (cmd == 2000)
	{
		// end
		maxCmd += 1;
		// printf("maxCmd=%d  itemNum=%d \n", maxCmd, itemNum);
		int LN = 4096 / (maxCmd * 4);
		unsigned int *tmp = (unsigned int *)malloc(4 * maxCmd * LN);
		int loopTimes = itemNum / LN + 1;
		int curIdx = 0, maxItemNum = itemNum * maxCmd;
		for (int lp = 0; lp < loopTimes && curIdx < maxItemNum; ++lp)
		{
			int tmpLen = 0;
			for (int i = 0; i < LN && curIdx < maxItemNum; ++i)
			{
				for (int j = 0; j < maxCmd && curIdx < maxItemNum; ++j)
				{
					unsigned int *bp = (unsigned int *)buffers[j];
					int idx = i + lp * LN;
					// printf("tmpLen=%d, idx=%d fmcd=%d  val=%d \n", tmpLen, idx, j, bp[idx]);
					tmp[tmpLen++] = bp[idx];
					++curIdx;
				}
			}
			fwrite(tmp, 4, tmpLen, file);
		}
		fclose(file);
		file = NULL;
		maxCmd = 0;
		return;
	}

	if (cmd == 0) {
		// is date
		itemNum = len;
		printf("Download start day: %d \n ", (int)val[0] + 19000000);
	}

	void *p = buffers[cmd];
	if (len < itemNum) {
		memset(buffers[cmd], 0, 4 * itemNum - len);
		p = (char *)buffers[cmd] + (itemNum - len) * 4;
	}

	if (type == 1) { // int
		int *pi = (int *)p;
		for (int i = 0; i < len; ++i) {
			pi[i] = (int)val[i];
			if (val[i] - pi[i] >= 0.5) {
				++pi[i];
			}
			//printf("%d %f \n", pi[i], val[i]);
		}
	} else if (type == 2) { // float
		memcpy(p, val, sizeof(float) * len);
	}
}

void TH_MAX_MIN_REF(int len, float *out, float *fcmd, float *val, float *c)
{
	//OpenIO();
	int cmd = (int)fcmd[len - 1];
	if (cmd == 1)
	{ // get max val
		float m = -3.4e+38F;
		for (int i = 0; i < len; ++i)
		{
			if (val[i] > m)
				m = val[i];
		}
		for (int i = 0; i < len; ++i)
		{
			out[i] = m;
		}
		return;
	}
	if (cmd == 2) { // get min val
		float m = 3.4e+38F;
		for (int i = 0; i < len; ++i)
		{
			if (val[i] < m)
				m = val[i];
		}
		for (int i = 0; i < len; ++i)
		{
			out[i] = m;
		}
		return;
	}
}

void JGD_REF(int len, float *out, float *fcmd, float *val, float *c) {
	GetJGD(len, out, fcmd, val, c);
}

//------------------------------------------------------------------------------
PluginTCalcFuncInfo g_CalcFuncSets[] = {
	{1, (pPluginFUNC)&BeginLock_REF},
	{2, (pPluginFUNC)&EndLock_REF},

	{120, (pPluginFUNC)&TdxZJ_REF},
	{122, (pPluginFUNC)&STRING_REF},
	{125, (pPluginFUNC)&THBJ_PM_REF},
	{126, (pPluginFUNC)&TH_NUM_REF},

	{130, (pPluginFUNC)&TH_DOWNLOAD_REF},

	{200, (pPluginFUNC)&JGD_REF},

	{500, (pPluginFUNC)&TH_MAX_MIN_REF},
	{0, NULL},
};

DLLIMPORT int RegisterTdxFunc(PluginTCalcFuncInfo** pFun) {
	if (*pFun == NULL) {
		(*pFun) = g_CalcFuncSets;
		InitHolidays();
		InitializeCriticalSection(&commMutex);
		return TRUE;
	}

	return FALSE;
}


//DLLIMPORT void HelloWorld () {}

BOOL APIENTRY DllMain (HINSTANCE hInst     /* Library instance handle. */ ,
                       DWORD reason        /* Reason this function is being called. */ ,
                       LPVOID reserved     /* Not used. */ )
{
	GetModuleFileNameA(hInst, DLL_PATH, sizeof(DLL_PATH));
	char *p = strrchr(DLL_PATH, '\\');
	if (p != NULL) {
		p[1] = 0;
	}
	
    switch (reason) {
      case DLL_PROCESS_ATTACH:
        break;

      case DLL_PROCESS_DETACH:
        break;
        
      case DLL_THREAD_ATTACH:
        break;

      case DLL_THREAD_DETACH:
        break;
    }
    
    /* Returns TRUE on success, FALSE on failure */
    return TRUE;
}
