#pragma once

void InitZJParam(int id, int val);

void InitZJParamDate(float* days, int len);

void CalcHgtZJ(float *out, int len);

void CalcHgtZJAbs(float *out, int len);

void GetZJMax(float *out, int len);

void GetThbjPM(int code, float *out, int len);

void GetThNum(int code, float *out, int len);

void CalcHgtCJJE(float *out, int len);

void CalcHgtAccZJ(float *out, int len);

void GetHgtAccCgsl(float *out, int len);

void GetHgtAccPer(float *out, int len);

void CalcCaoDie(float *out, int len, float *bbi, float *downBoll);