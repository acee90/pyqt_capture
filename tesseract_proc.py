
import sys
from multiprocessing import Process, Queue

import pytesseract

def producer(input_q: Queue, output_q: Queue):
    pytesseract.pytesseract.tesseract_cmd = r'.\Tesseract-OCR\tesseract.exe'
    
    while True:
        if not input_q.empty():
            print('producer run', getattr(sys, 'frozen', False))

            custom_config = r'--oem 3 --psm 6 --tessdata-dir "Tesseract-OCR\\tessdata"'

            img = input_q.get()
            ret = pytesseract.image_to_string(
                img, lang='eng+kor', config=custom_config)
            
            output_q.put(ret)
