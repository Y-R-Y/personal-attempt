package com.example.cnnfilter;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Spinner;

import androidx.appcompat.app.AppCompatActivity;

import com.example.cnnfilter.databinding.ActivityMainBinding;

import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;

/**
 * 主界面：左右对比显示输入和输出图片，下方显示 PSNR 指标。
 *
 * PSNR 计算逻辑与训练代码完全一致：
 *   rgb_psnr       = psnr(prediction, target)  → 输出 vs 高质量原图
 *   rgb_psnr_gain  = rgb_psnr(output, target) - rgb_psnr(input, target) → 增益
 *   y_psnr         = psnr(Y通道(output), Y通道(target)) → 亮度通道
 *
 * 三种使用模式：
 * 1. 内置测试图（source + label 配对）→ 完整 PSNR + gain
 * 2. 用户自选图（只有 source，无 label）→ 只显示 PSNR(output, input) 和 SSIM
 */
public class MainActivity extends AppCompatActivity {
    private static final String TAG = "MainActivity";
    private static final int PICK_IMAGE = 1001;

    // 内置测试图样本名（assets/test/ 目录下的配对图片）
    private static final String[] TEST_SAMPLES = {
        "CrowdRun_1920x1080_0001",
        "Motorcycle_1920x1080_30fps_8bit_0001",
        "MountainBike_1920x1080_30fps_8bit_0001",
        "OldTownCross_1920x1080p50_0001",
        "PedestrianArea_1920x1080p25_0001",
        "Riverbed_1920x1080p25_0001",
        "RushFieldCuts_1920x1080_2997_0001",
        "TreesAndGrass_1920x1080_30fps_8bit_0001",
    };

    private ORTInferenceEngine engine;
    private ActivityMainBinding binding;
    private Bitmap selectedSource;  // 输入图 (source/anchor)
    private Bitmap groundTruth;     // 高质量原图 (target/label)，内置测试图才有
    private boolean hasGroundTruth; // 是否有配对的 label 图

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        // Spinner 选择内置测试图
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
            android.R.layout.simple_spinner_item, TEST_SAMPLES);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        binding.spinnerSamples.setAdapter(adapter);
        binding.spinnerSamples.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                loadTestSample(TEST_SAMPLES[position]);
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        // 初始化推理引擎
        new Thread(() -> {
            try {
                engine = new ORTInferenceEngine();
                engine.init(this);
                runOnUiThread(() -> {
                    binding.btnProcess.setEnabled(true);
                    binding.tvInfo.setText(engine.isNpuActive() ? "NPU ✅" : "CPU ⚠️");
                });
            } catch (Exception e) {
                Log.e(TAG, "初始化失败", e);
                StringWriter sw = new StringWriter();
                PrintWriter pw = new PrintWriter(sw);
                e.printStackTrace(pw);
                runOnUiThread(() -> binding.tvInfo.setText("初始化失败:\n" + sw.toString()));
            }
        }).start();

        binding.btnPick.setOnClickListener(v -> pickImage());
        binding.btnProcess.setOnClickListener(v -> processImage());
    }

    /**
     * 从 assets 加载内置测试样本（source + label 配对）
     */
    private void loadTestSample(String sampleName) {
        new Thread(() -> {
            try {
                String sourcePath = "test/rec/" + sampleName + ".png";
                String labelPath = "test/label/" + sampleName + ".png";

                selectedSource = ORTInferenceEngine.loadBitmapFromAssets(this, sourcePath);
                groundTruth = ORTInferenceEngine.loadBitmapFromAssets(this, labelPath);

                hasGroundTruth = (selectedSource != null && groundTruth != null);

                runOnUiThread(() -> {
                    if (selectedSource != null) {
                        binding.ivInput.setImageBitmap(selectedSource);
                        binding.tvInputInfo.setText("输入 " + selectedSource.getWidth() + "×" + selectedSource.getHeight());
                    } else {
                        binding.tvInputInfo.setText("加载失败");
                    }
                });
            } catch (Exception e) {
                Log.e(TAG, "加载样本失败: " + e.getMessage());
            }
        }).start();
    }

    /**
     * 用户自选图片（没有配对的 label）
     */
    private void pickImage() {
        Intent intent = new Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
        intent.setType("image/*");
        startActivityForResult(intent, PICK_IMAGE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_IMAGE && resultCode == RESULT_OK && data != null) {
            try {
                Uri uri = data.getData();
                InputStream is = getContentResolver().openInputStream(uri);
                selectedSource = BitmapFactory.decodeStream(is);
                is.close();
                groundTruth = null;
                hasGroundTruth = false;

                binding.ivInput.setImageBitmap(selectedSource);
                binding.tvInputInfo.setText("输入 " + selectedSource.getWidth() + "×" + selectedSource.getHeight());
            } catch (Exception e) {
                binding.tvInfo.setText("图片加载失败: " + e.getMessage());
            }
        }
    }

    private void processImage() {
        if (engine == null || selectedSource == null) {
            binding.tvInfo.setText("请先选择图片");
            return;
        }

        binding.progressBar.setVisibility(View.VISIBLE);
        binding.btnProcess.setEnabled(false);

        Bitmap source = selectedSource;
        Bitmap label = groundTruth;
        boolean hasLabel = hasGroundTruth;

        new Thread(() -> {
            try {
                long start = System.currentTimeMillis();
                Bitmap output = engine.infer(source);
                long elapsed = System.currentTimeMillis() - start;

                String inputText;
                String outputText;

                if (hasLabel) {
                    // ===== 有 ground_truth：与训练代码完全一致的 PSNR 计算 =====
                    double inputPsnr = ImageUtils.rgbPsnr(source, label);
                    double outputPsnr = ImageUtils.rgbPsnr(output, label);
                    double psnrGain = ImageUtils.rgbPsnrGain(outputPsnr, inputPsnr);

                    double inputYPsnr = ImageUtils.yPsnr(source, label);
                    double outputYPsnr = ImageUtils.yPsnr(output, label);
                    double yPsnrGain = outputYPsnr - inputYPsnr;

                    // 输入侧：显示 y_psnr 和 rgb_psnr
                    inputText = String.format("输入 PSNR: %.2f (Y: %.2f)", inputPsnr, inputYPsnr);

                    // 输出侧：显示 rgb_psnr、增益、y_psnr、推理耗时
                    outputText = String.format("PSNR: %.2f (Y: %.2f) | 增益: +%.4f (+%.4f) | %dms",
                        outputPsnr, outputYPsnr, psnrGain, yPsnrGain, elapsed);
                } else {
                    // ===== 无 ground_truth：只能算 output vs source 的 PSNR =====
                    double psnr = ImageUtils.rgbPsnr(output, source);
                    double yPsnr = ImageUtils.yPsnr(output, source);

                    inputText = String.format("输入 (无label)");
                    outputText = String.format("PSNR(out,in): %.2f (Y: %.2f) | %dms", psnr, yPsnr, elapsed);
                }

                runOnUiThread(() -> {
                    binding.ivOutput.setImageBitmap(output);
                    binding.tvInputInfo.setText(inputText);
                    binding.tvOutputInfo.setText(outputText);
                    binding.progressBar.setVisibility(View.GONE);
                    binding.btnProcess.setEnabled(true);
                    binding.tvInfo.setText(engine.isNpuActive() ? "NPU ✅" : "CPU ⚠️");
                });
            } catch (Exception e) {
                StringWriter sw = new StringWriter();
                PrintWriter pw = new PrintWriter(sw);
                e.printStackTrace(pw);
                runOnUiThread(() -> {
                    binding.progressBar.setVisibility(View.GONE);
                    binding.btnProcess.setEnabled(true);
                    binding.tvInfo.setText("推理失败:\n" + sw.toString());
                });
            }
        }).start();
    }

    @Override
    protected void onDestroy() {
        if (engine != null) engine.close();
        super.onDestroy();
    }
}