😔

1. Under UnifiedGUI\frontend\lib, update config.ts to have selected IP address (do ipconfig in cmd and select the port in either ethernet or wifi)
2. cd .\UnifiedGUI\frontend\
3. npm run dev:network

4. cd .\UnifiedGUI\backend
5. python main.py

Open up your ip address and at port 3000 


Make sure URX library is updated for getl and does not return errors or many of the functions will not work. pip install urx in venv, and edit robot.py in urx folder in .venv\lib\site-packages\urx\robot.py. On line 211 for getL function, change to "return t.pose_vector.get_array().tolist()" and it should work.


If you get AttributeError: 'PoseVector' object has no attribute 'tolist', you did not update the URX library error.

**6. Don't blow up the reactor.**


Unified GUI has the typescript webserver, with fastapi backend that CALLS robot_functions in UR_Cold_Spray_Code folder. Python GUI includes the camera backend that calls HTI thermal camera. UR_Control_Code has things regarding space mouse and thermal tracking in 2D plane view. Sorry Russel. Wish I could have kept it cleaner but we worked on it too seperately and design changes were made too often to make a finalized setup for the UR + Kuka. 