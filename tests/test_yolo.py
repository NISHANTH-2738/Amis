# test_yolo.py
import yolov5

model = yolov5.load('yolov5s.pt')
results = model('test.jpg')

results.print()cd yolov