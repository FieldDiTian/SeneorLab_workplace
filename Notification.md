One windows is for marlin compeling
The other one is for python coding

Motorcontroller is main function, with a well settled class motorcontroller.
You can directly import motorcontroller as mc() then use it to function
We have an example in test.py(dont use test_xyz,not debug yet)
 
Remember the red light next to cpu, when it is runing well, it should be very bright. If it's faded, then something going wrong with Gcode(we are using python code to run Gcode so its a promramming issues（or could be my bad with firmwarm XD）). When this happenes, set board to DFU mode and upload the firmwarm again(Uploading firmwarm will be like:).
--- 
================================== [FAILED] Took 131.97 seconds ==================================

Environment      Status    Duration
---------------  --------  ------------
STM32H723ZE_btt  FAILED    00:02:11.966
============================== 1 failed, 0 succeeded in 00:02:11.966 ==============================
---
It's normal. If you see
--- 
Download        [=========================] 100%       114592 bytes
Download done.
File downloaded successfully
--- 
Then it's good.

By Di Tian in 10/15/2025
