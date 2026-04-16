# EIS 图像绘制原理说明 / EIS Plotting Principles

本文档总结当前 EIS 图像的绘制流程、每个子图的含义，以及谐波分析的基本原理。  
This document summarizes how the current EIS figures are generated, what each subplot means, and the basic principle behind the harmonic analysis.

对应实现主要位于 `modules/eis_module.py`。  
The main implementation is in `modules/eis_module.py`.

## 1. 当前输出图像的结构 / Current Figure Layout

每个频率点会输出一张 `UI_*.png`，采用 `2 x 2` 布局。  
Each frequency point generates one `UI_*.png` figure with a `2 x 2` layout.

- 左上：`U(t) Raw`
  显示样品电压 `v_sample` 的原始真实 5 周期波形  
  Top-left: `U(t) Raw`
  Shows the raw measured 5-cycle waveform of the sample voltage `v_sample`

- 左下：`I(t) Raw`
  显示样品电流 `i_t` 的原始真实 5 周期波形  
  Bottom-left: `I(t) Raw`
  Shows the raw measured 5-cycle waveform of the sample current `i_t`

- 右上：`U(t) Fundamental Sine`
  显示电压的基波正弦参考波形  
  Top-right: `U(t) Fundamental Sine`
  Shows the fundamental sine reference reconstructed from the voltage

- 右下：`I(t) Harmonic Basis`
  显示电流的谐波分析代表波形，并标注 `THD`  
  Bottom-right: `I(t) Harmonic Basis`
  Shows the representative current waveform used for harmonic analysis, with `THD`

这样设计的目的是：左侧保留真实采样结果，右侧给出分析结果。  
This layout is designed so that the left column preserves the real measured waveform, while the right column shows the analysis-oriented waveform.

## 2. 采样信号从哪里来 / Where the Signals Come From

当前代码默认接线假设为：  
The current code assumes the following wiring:

```text
Wavegen -> Rs -> Sample
           |      |
          CH0    CH1
```

对应定义如下：  
The corresponding signal definitions are:

- `CH0`：激励端电压 `Vin`  
  `CH0`: excitation/input voltage `Vin`

- `CH1`：样品端电压 `Vs`  
  `CH1`: sample-side voltage `Vs`

- 串联电阻压降：`Vr = Vin - Vs`  
  Series resistor voltage: `Vr = Vin - Vs`

- 电流：`I = Vr / Rs = (CH0 - CH1) / Rs`  
  Current: `I = Vr / Rs = (CH0 - CH1) / Rs`

因此图中的电压和电流分别是：  
Therefore, the plotted voltage and current are:

- `U(t)`：样品两端电压 `Vs`  
  `U(t)`: sample voltage `Vs`

- `I(t)`：通过串联电阻推算得到的样品电流  
  `I(t)`: sample current inferred from the series resistor

## 3. 为什么只看最后 5 个周期 / Why Only the Last 5 Cycles Are Shown

图中左侧 `Raw` 波形不是整段录波，而是稳态末尾的 5 个周期。  
The `Raw` waveforms on the left are not the entire recording; they are the last 5 cycles in steady state.

原因是：  
The reason is:

- 波形刚启动时会有瞬态  
  The waveform contains startup transient behavior at the beginning

- 瞬态不代表稳定的 EIS 响应  
  The transient does not represent the steady-state EIS response

- 只看末尾 5 周期，更接近真正稳态  
  The last 5 cycles are closer to the true steady-state response

当前绘图策略是：  
The current plotting strategy is:

1. 先完整录制若干周期  
   First record multiple cycles
2. 丢弃前面的启动/过渡段  
   Then discard the startup/transient portion
3. 只截取最后 5 个周期做显示和分析  
   Finally use only the last 5 cycles for display and analysis

## 4. 左侧 Raw 图是怎么画的 / How the Raw Plots on the Left Are Drawn

左侧两张图直接使用末尾 5 周期的原始采样值：  
The two plots on the left directly use the raw sampled values from the last 5 cycles:

- `U(t) Raw`：直接画 `v_sample`  
  `U(t) Raw`: directly plots `v_sample`

- `I(t) Raw`：直接画 `i_t = (CH0 - CH1) / Rs`  
  `I(t) Raw`: directly plots `i_t = (CH0 - CH1) / Rs`

这里不做平均、不做平滑、不做人为正弦化。  
No averaging, smoothing, or artificial sinusoidal reconstruction is applied here.

它们用来回答：  
These plots are used to answer:

- 真实采样波形长什么样  
  What does the true sampled waveform look like?

- 当前噪声有多大  
  How much noise is present?

- 原始波形是否能肉眼看出失真  
  Is distortion visible directly in the raw waveform?

## 5. 为什么右上电压图是标准正弦 / Why the Voltage Plot on the Top Right Is a Pure Sine

用户目标是：  
The target behavior is:

- 电压应接近标准正弦  
  The voltage should be close to an ideal sine wave

- 电流允许存在谐波  
  The current may contain harmonics

因此右上 `U(t) Fundamental Sine` 不再使用原始电压或电压失真代表波形，而是只保留电压的 `1x` 基波。  
Therefore, the top-right plot `U(t) Fundamental Sine` does not use the raw voltage or a distorted representative voltage waveform. It keeps only the `1x` fundamental component of the voltage.

做法是：  
The method is:

1. 取末尾 5 个周期的电压数据  
   Take the voltage data from the last 5 cycles
2. 估计电压的基波幅值和相位  
   Estimate the amplitude and phase of the voltage fundamental
3. 只保留基波项  
   Keep only the fundamental term
4. 重建标准正弦单周期  
   Reconstruct a pure sine-wave cycle
5. 重复显示成 5 个周期  
   Repeat it to display 5 cycles

所以右上图的意义是“电压基波参考”，而不是“电压原始波形”。  
So the top-right plot is a reference sine wave for the voltage fundamental, not the raw voltage waveform.

## 6. 为什么右下电流图可以显示谐波 / Why the Bottom-Right Current Plot Can Show Harmonics

右下 `I(t) Harmonic Basis` 的目标不是保留所有随机噪声，而是保留稳定重复的非正弦成分。  
The purpose of the bottom-right plot `I(t) Harmonic Basis` is not to preserve all random noise, but to preserve the stable, repeatable non-sinusoidal part of the current.

为此，代码会先构造一个代表性单周期：  
To do this, the code builds a representative single cycle:

1. 取末尾 5 个周期的电流数据  
   Take the current data from the last 5 cycles
2. 按基波相位对每个周期做对齐  
   Align the cycles by the fundamental phase
3. 将各周期重采样到统一相位网格  
   Resample each cycle onto the same phase grid
4. 对这些周期求平均  
   Average the aligned cycles
5. 得到一个代表性单周期  
   Obtain one representative cycle
6. 再把它重复成 5 个周期显示  
   Repeat it to show 5 cycles

这样做的好处是：  
This has several benefits:

- 随机噪声会被压低  
  Random noise is reduced

- 周期周期都重复出现的失真会保留下来  
  Distortion that repeats every cycle is preserved

- 更容易看出谐波引起的肩部、双峰、扁顶等变化  
  Harmonic-induced shoulders, double peaks, flat tops, and similar distortions become easier to see

## 7. THD 是什么 / What THD Means

`THD` 表示总谐波失真，英文是 `Total Harmonic Distortion`。  
`THD` stands for `Total Harmonic Distortion`.

定义为：  
It is defined as:

```text
THD = sqrt(I2^2 + I3^2 + I4^2 + I5^2 + ...) / I1
```

其中：  
where:

- `I1`：基波幅值  
  `I1`: fundamental amplitude

- `I2`：二次谐波幅值  
  `I2`: second harmonic amplitude

- `I3`：三次谐波幅值  
  `I3`: third harmonic amplitude

- `I4`：四次谐波幅值  
  `I4`: fourth harmonic amplitude

- `I5`：五次谐波幅值  
  `I5`: fifth harmonic amplitude

`THD` 越大，说明波形偏离纯正弦越明显。  
The larger the `THD`, the farther the waveform is from a pure sine wave.

当前实现中：  
In the current implementation:

- 图上的 `THD`  
  the `THD` shown in the figure

- `EIS_Harmonics_*.txt` 中的 `THD_pct`  
  and `THD_pct` in `EIS_Harmonics_*.txt`

都来自同一份代表性电流单周期。  
both come from the same representative current cycle.

## 8. 为什么 Peak 不一定等于 I1 / Why Peak Is Not Necessarily Equal to I1

需要区分两个量：  
Two quantities should be distinguished:

- `Peak`：时域波形的总峰值  
  `Peak`: the overall time-domain peak value

- `I1`：基波的峰值幅度  
  `I1`: the peak amplitude of the fundamental component

如果波形中含有谐波，那么总峰值可能大于基波峰值。  
If the waveform contains harmonics, the overall peak can be larger than the fundamental peak.

原因是谐波会改变波峰形状。  
This happens because harmonics reshape the waveform peak.

所以：  
Therefore:

- `Peak` 反映整条波形最高能到哪里  
  `Peak` tells you how high the full waveform reaches

- `I1` 反映其中的基波有多强  
  `I1` tells you how strong the fundamental is

两者不必相等。  
They do not need to be equal.

## 9. 为什么低频往往看不出谐波 / Why Harmonics Are Often Hard to See at Low Frequency

低频下常见现象是：  
At low frequency, the typical behavior is:

- 系统更接近线性响应  
  the system behaves more linearly

- 基波占主导  
  the fundamental dominates

- 高次谐波相对很小  
  higher harmonics remain relatively small

这时即使存在少量谐波，时域上通常仍然看起来像正弦。  
In that case, even if some harmonics exist, the waveform still looks nearly sinusoidal in the time domain.

而在高频下，更容易暴露：  
At high frequency, it is easier to expose:

- 电极/界面非理想性  
  electrode/interface non-idealities

- 寄生电容和寄生电感  
  parasitic capacitance and inductance

- 动态极化效应  
  dynamic polarization effects

- 高频非线性  
  high-frequency nonlinearities

所以高频更容易出现明显谐波。  
That is why harmonics are often more visible at high frequency.

## 10. 当前图像的解读建议 / How to Read the Current Figures

建议按这个顺序看图：  
It is recommended to read the figure in this order:

1. 先看左侧 Raw  
   First look at the left `Raw` plots

2. 再看右上 Fundamental Sine  
   Then look at the top-right `Fundamental Sine`

3. 最后看右下 Harmonic Basis  
   Finally look at the bottom-right `Harmonic Basis`

具体来说：  
Specifically:

- 左侧看真实数据和噪声  
  The left side shows the true waveform and noise

- 右上看电压是否接近标准正弦  
  The top-right shows whether the voltage is close to an ideal sine

- 右下看电流是否存在稳定谐波  
  The bottom-right shows whether the current contains stable harmonics

## 11. 当前会输出哪些文件 / Current Output Files

当前 EIS 流程会输出：  
The current EIS workflow outputs:

- `UI_*.png`
  每个频率的 `2 x 2` 对照图  
  A `2 x 2` comparison plot for each frequency

- `EIS_Data_*.txt`
  阻抗数据文件  
  Impedance data file

- `EIS_Harmonics_*.txt`
  谐波幅值与 `THD` 数据文件  
  Harmonic amplitude and `THD` data file

## 12. 一句话总结 / One-Sentence Summary

当前图像不是简单地“把原始波形画出来”，而是把：  
The current figure is not simply “a plot of the raw waveform”; instead, it combines:

- 原始真实波形  
  the raw measured waveform

- 电压基波正弦参考  
  a pure fundamental sine reference for the voltage

- 电流谐波分析结果  
  the harmonic-analysis waveform of the current

放在同一张图里，用来同时回答三个问题：  
in one figure, so that it can answer three questions at once:

1. 真正采到了什么  
   What was actually measured?
2. 电压是否接近标准正弦  
   Is the voltage close to an ideal sine wave?
3. 电流是否存在稳定高次谐波  
   Does the current contain stable higher-order harmonics?
