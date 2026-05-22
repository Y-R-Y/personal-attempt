package com.example.cnnfilter;

import android.graphics.Bitmap;
import android.graphics.Color;

/**
 * 图像转换工具 + PSNR/SSIM 计算，与训练代码 metrics.py 逻辑一致。
 *
 * 训练代码中的 PSNR 计算：
 *   rgb_psnr(prediction, target) = 10 * log10(255^2 / MSE)
 *   MSE = mean((prediction*255 - target*255)^2) 对 RGB 三通道平均
 *   rgb_psnr_gain = rgb_psnr(output, target) - rgb_psnr(input, target)
 */
public class ImageUtils {

    /**
     * Bitmap (ARGB_8888) → float[1, 3, H, W]
     * RGB 通道，normalize 到 [0.0, 1.0]，CHW layout
     */
    public static float[] bitmapToCHWFloat(Bitmap bitmap) {
        int w = bitmap.getWidth();
        int h = bitmap.getHeight();
        float[] result = new float[3 * h * w];

        int[] pixels = new int[w * h];
        bitmap.getPixels(pixels, 0, w, 0, 0, w, h);

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int px = pixels[y * w + x];
                int rIdx = 0 * h * w + y * w + x;
                int gIdx = 1 * h * w + y * w + x;
                int bIdx = 2 * h * w + y * w + x;
                result[rIdx] = ((px >> 16) & 0xFF) / 255.0f;
                result[gIdx] = ((px >>  8) & 0xFF) / 255.0f;
                result[bIdx] = ((px      ) & 0xFF) / 255.0f;
            }
        }
        return result;
    }

    /**
     * float[1, 3, H, W] → Bitmap (ARGB_8888)
     * CHW → HWC, clamp [0, 1], ×255
     */
    public static Bitmap chwFloatToBitmap(float[] data, int w, int h) {
        int[] pixels = new int[w * h];

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int rIdx = 0 * h * w + y * w + x;
                int gIdx = 1 * h * w + y * w + x;
                int bIdx = 2 * h * w + y * w + x;

                int r = clamp255(data[rIdx] * 255.0f);
                int g = clamp255(data[gIdx] * 255.0f);
                int b = clamp255(data[bIdx] * 255.0f);

                pixels[y * w + x] = Color.rgb(r, g, b);
            }
        }

        Bitmap bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        bitmap.setPixels(pixels, 0, w, 0, 0, w, h);
        return bitmap;
    }

    private static int clamp255(float v) {
        return Math.max(0, Math.min(255, Math.round(v)));
    }

    // ================================================================
    // PSNR 计算 — 与训练代码 metrics.py 中 rgb_psnr 完全一致
    // ================================================================

    /**
     * RGB PSNR，与训练代码 metrics.py 中 rgb_psnr 一致：
     * PSNR = 10 * log10(255^2 / MSE)
     * MSE = mean((prediction*255 - target*255)^2) 对 RGB 三通道
     *
     * @param prediction 模型输出或输入图（Bitmap，像素 0~255）
     * @param target     ground_truth 高质量原图（Bitmap，像素 0~255）
     * @return PSNR 值，两图完全相同时返回 POSITIVE_INFINITY
     */
    public static double rgbPsnr(Bitmap prediction, Bitmap target) {
        int w = prediction.getWidth();
        int h = prediction.getHeight();

        int[] predPixels = new int[w * h];
        int[] targPixels = new int[w * h];
        prediction.getPixels(predPixels, 0, w, 0, 0, w, h);
        target.getPixels(targPixels, 0, w, 0, 0, w, h);

        double mse = 0.0;
        for (int i = 0; i < w * h; i++) {
            double pr = (predPixels[i] >> 16) & 0xFF;
            double pg = (predPixels[i] >> 8) & 0xFF;
            double pb = predPixels[i] & 0xFF;

            double tr = (targPixels[i] >> 16) & 0xFF;
            double tg = (targPixels[i] >> 8) & 0xFF;
            double tb = targPixels[i] & 0xFF;

            double dr = pr - tr;
            double dg = pg - tg;
            double db = pb - tb;

            mse += (dr * dr + dg * dg + db * db) / 3.0;
        }

        mse /= (w * h);

        if (mse == 0) return Double.POSITIVE_INFINITY;
        return 10.0 * Math.log10(255.0 * 255.0 / mse);
    }

    /**
     * RGB PSNR 增益，与训练代码 status.py 中 _resolve_gain_status 一致：
     * gain = rgb_psnr(output, target) - rgb_psnr(input, target)
     *
     * @param outputPSNR  模型输出 vs ground_truth 的 PSNR
     * @param inputPSNR   输入图 vs ground_truth 的 PSNR
     * @return 增益值，正值表示模型提升了质量
     */
    public static double rgbPsnrGain(double outputPSNR, double inputPSNR) {
        return outputPSNR - inputPSNR;
    }

    /**
     * Y PSNR（BT.601 亮度通道），与训练代码 metrics.py 中 y_psnr 一致：
     * Y = 16 + 65.481*R + 128.553*G + 24.966*B (R,G,B in 0~1)
     * 然后对 Y 通道计算 PSNR，max_value=255
     */
    public static double yPsnr(Bitmap prediction, Bitmap target) {
        int w = prediction.getWidth();
        int h = prediction.getHeight();

        int[] predPixels = new int[w * h];
        int[] targPixels = new int[w * h];
        prediction.getPixels(predPixels, 0, w, 0, 0, w, h);
        target.getPixels(targPixels, 0, w, 0, 0, w, h);

        double mse = 0.0;
        for (int i = 0; i < w * h; i++) {
            // RGB 0~1
            double pr = ((predPixels[i] >> 16) & 0xFF) / 255.0;
            double pg = ((predPixels[i] >> 8) & 0xFF) / 255.0;
            double pb = (predPixels[i] & 0xFF) / 255.0;

            double tr = ((targPixels[i] >> 16) & 0xFF) / 255.0;
            double tg = ((targPixels[i] >> 8) & 0xFF) / 255.0;
            double tb = (targPixels[i] & 0xFF) / 255.0;

            // BT.601: Y = 16 + 65.481*R + 128.553*G + 24.966*B
            double predY = 16.0 + 65.481 * pr + 128.553 * pg + 24.966 * pb;
            double targY = 16.0 + 65.481 * tr + 128.553 * tg + 24.966 * tb;

            double dy = predY - targY;
            mse += dy * dy;
        }

        mse /= (w * h);

        if (mse == 0) return Double.POSITIVE_INFINITY;
        return 10.0 * Math.log10(255.0 * 255.0 / mse);
    }
}