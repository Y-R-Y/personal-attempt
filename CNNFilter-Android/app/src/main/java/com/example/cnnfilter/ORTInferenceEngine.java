package com.example.cnnfilter;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.Log;

import ai.onnxruntime.*;
import ai.onnxruntime.providers.NNAPIFlags;

import java.io.InputStream;
import java.nio.FloatBuffer;
import java.util.Collections;
import java.util.EnumSet;

/**
 * ONNX Runtime 推理引擎，NNAPI EP 加速骁龙 NPU，失败时自动回退 CPU。
 */
public class ORTInferenceEngine implements AutoCloseable {
    private static final String TAG = "ORTInference";
    private static final String MODEL_FILE = "model.fp32.onnx";
    private static final String INPUT_NAME = "input";
    private static final String OUTPUT_NAME = "output";

    private OrtEnvironment env;
    private OrtSession session;
    private boolean npuActive = false;

    /**
     * 初始化 ORT 环境 + 加载模型。
     * 先尝试 NNAPI (NPU)，失败则回退纯 CPU。
     * 必须在后台线程调用。
     */
    public void init(Context context) throws Exception {
        env = OrtEnvironment.getEnvironment();
        byte[] modelBytes = readModelFromAssets(context);

        // ---- 第一步：尝试 NNAPI EP ----
        try {
            OrtSession.SessionOptions nnapiOpts = new OrtSession.SessionOptions();
            EnumSet<NNAPIFlags> flags = EnumSet.of(NNAPIFlags.USE_FP16);
            nnapiOpts.addNnapi(flags);
            session = env.createSession(modelBytes, nnapiOpts);
            npuActive = true;
            Log.i(TAG, "✅ NNAPI EP 已挂载，NPU 加速");
        } catch (Exception e) {
            Log.w(TAG, "NNAPI EP 不可用: " + e.getMessage());
            npuActive = false;
        }

        // ---- 第二步：NNAPI 失败则纯 CPU ----
        if (!npuActive) {
            try {
                OrtSession.SessionOptions cpuOpts = new OrtSession.SessionOptions();
                session = env.createSession(modelBytes, cpuOpts);
                Log.i(TAG, "✅ 纯 CPU 模式加载成功");
            } catch (Exception e2) {
                Log.e(TAG, "❌ CPU 模式也失败: " + e2.getMessage());
                throw e2;
            }
        }

        Log.i(TAG, "输入: " + session.getInputNames());
        Log.i(TAG, "输出: " + session.getOutputNames());
        Log.i(TAG, "执行模式: " + (npuActive ? "NPU" : "CPU"));
    }

    /**
     * 执行推理：Bitmap 输入 → Bitmap 输出。
     */
    public Bitmap infer(Bitmap inputBitmap) throws OrtException {
        int width = inputBitmap.getWidth();
        int height = inputBitmap.getHeight();

        float[] inputData = ImageUtils.bitmapToCHWFloat(inputBitmap);

        long[] shape = {1, 3, height, width};
        OnnxTensor inputTensor = OnnxTensor.createTensor(
            env, FloatBuffer.wrap(inputData), shape
        );

        OrtSession.Result result = session.run(
            Collections.singletonMap(INPUT_NAME, inputTensor)
        );

        OnnxTensor outputTensor = (OnnxTensor) result.get(OUTPUT_NAME).get();
        float[] outputData = new float[outputTensor.getFloatBuffer().remaining()];
        outputTensor.getFloatBuffer().get(outputData);

        Bitmap outputBitmap = ImageUtils.chwFloatToBitmap(outputData, width, height);

        inputTensor.close();
        result.close();

        return outputBitmap;
    }

    public boolean isNpuActive() {
        return npuActive;
    }

    /**
     * 从 assets 加载图片 Bitmap。
     */
    public static Bitmap loadBitmapFromAssets(Context context, String path) {
        try {
            InputStream is = context.getAssets().open(path);
            Bitmap bitmap = BitmapFactory.decodeStream(is);
            is.close();
            return bitmap;
        } catch (Exception e) {
            Log.e(TAG, "加载图片失败: " + path + " - " + e.getMessage());
            return null;
        }
    }

    private byte[] readModelFromAssets(Context context) throws Exception {
        InputStream is = context.getAssets().open(MODEL_FILE);
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        byte[] tmp = new byte[8192];
        int n;
        while ((n = is.read(tmp)) != -1) {
            bos.write(tmp, 0, n);
        }
        is.close();
        byte[] buffer = bos.toByteArray();
        bos.close();
        Log.i(TAG, "模型大小: " + buffer.length + " bytes");
        return buffer;
    }

    @Override
    public void close() {
        if (session != null) {
            try {
                session.close();
                Log.i(TAG, "Session 已关闭");
            } catch (OrtException e) {
                Log.w(TAG, "关闭 Session 异常: " + e.getMessage());
            }
        }
    }
}