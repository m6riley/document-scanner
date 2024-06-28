#Import modules:
import zxingcpp as reader
import os
import cv2
import pytesseract
import csv
import re


#Folder names:
input_folder = 'Documents'
failure_folder = 'failure'
success_folder = 'success'

#Debug variables"
number_success = 0
number_failure = 0

#Read in documents:
documents_paths = []
for file in os.listdir(input_folder):
    file_path = os.path.join(input_folder, file) 
    documents_paths.append(file_path)


#Open results csv file and declare writer object:
with open('results.csv', 'a') as results:
    writer = csv.DictWriter(results, fieldnames= ['ID', 'PHN', 'PatientName', 'BirthDate', 'Account', 'CDC', 'Specimen', 'From', 'Tests', 'CollectionDate', 'CollectionTime'])

    for i in range(len(documents_paths)):

        #Open document image as opencv array. Read barcodes into document_bar:
        document_bar = reader.read_barcodes(cv2.imread(documents_paths[i]))

        #Dictionary to hold values (Note: To make a barcode field optional, fill in a default value below):
        new_row = {
            'ID': '',
            'PHN': '',
            'PatientName': '',
            'BirthDate': '',
            'Account': '',
            'CDC': 'Not Found',
            'Specimen': '',
            'From': '',
            'Tests': '',
            'CollectionDate': '',
            'CollectionTime': ''
        }
        #Match text with dictionary values:
        for value in document_bar:
            if (len(value.text) == 6 and value.text.isdigit() == True):
                new_row['ID'] = value.text
            elif (value.text.find('YK') != -1):
                new_row['PHN'] = value.text
            elif (value.text.find(',') != -1):
                new_row['PatientName'] = value.text
            elif (value.text.count('/') == 2):
                new_row['BirthDate'] = value.text
            elif (value.text.count('/') == 1):
                new_row['Account'] = value.text
            elif (value.text.find(':') != -1 and value.text.find(';') != -1):
                new_row['Specimen'] = value.text
            elif ((len(value.text) == 6 and value.text.isdigit() == False)):
                new_row['CDC'] = value.text

        #Read document text with Tesseract OCR:
        document_ocr = pytesseract.image_to_string(cv2.imread(documents_paths[i])).splitlines()
        document_from = ''
        document_tests = ''
        document_date = ''
        document_time = ''

        #Extract values from text:
        for a in range(len(document_ocr)):
            if (document_ocr[a].find('From:') != -1):
                document_from = document_ocr[a][5:]
            elif (document_ocr[a].find('COLLECTION DATE:') != -1):
                document_date = document_ocr[a][16:document_ocr[a].rfind('/') + 5].strip()
                document_time = document_ocr[a][document_ocr[a].find('TIME:') + 5:].strip()[:4]

            elif (document_ocr[a].find('site') != -1):
                n = a + 1
                while(document_ocr[n].strip() == "" and n < len(document_ocr)):
                    n += 1 
                document_tests = document_ocr[n]

        #Clean from text:
        document_from = document_from.strip()
        document_from = re.sub(r'[^a-zA-Z ]', '', document_from)
        #Clean tests text:
        document_tests = document_tests.strip()
        document_tests = document_tests[:document_tests.rfind(']') + 1]
        #Clean date text
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for month in months:
            if (document_date[document_date.find('/'):document_date.rfind('/')].find(month) != -1):
                document_date = document_date[:document_date.find('/') + 1] + month + document_date[document_date.rfind('/'):]
                break
        #Add OCR values to dictionary:
        new_row['From'] = document_from
        new_row['Tests'] = document_tests
        new_row['CollectionDate'] = document_date
        new_row['CollectionTime'] = document_time
        #Verify values are were read and are correct (e.g. manage edge cases). Move document to failure folder if not:
        #Check if barcode values are missing:
        if any(value.strip() == '' for value in new_row.values()) :
            os.replace(documents_paths[i], os.path.join(failure_folder, os.path.basename(documents_paths[i])))
            writer.writerow(new_row)
            number_failure += 1
        #Check is collection time is numeric:
        elif (document_time.isnumeric() == False):
            os.replace(documents_paths[i], os.path.join(failure_folder, os.path.basename(documents_paths[i])))
            writer.writerow(new_row)
            number_failure += 1
        #Edge cases for collection date:
        elif (len(document_date) != 11 or document_date[document_date.rfind('/'):].isnumeric() == True):
            os.replace(documents_paths[i], os.path.join(failure_folder, os.path.basename(documents_paths[i])))
            writer.writerow(new_row)
            number_failure += 1
        #Edge cases for tests:
        elif (document_tests.find(']') == -1 or document_tests.find('[') == -1 or (document_tests.count('[') + document_tests.count(']'))%2 != 0):
            os.replace(documents_paths[i], os.path.join(failure_folder, os.path.basename(documents_paths[i])))
            writer.writerow(new_row)
            number_failure += 1
        #If all tests pass, move document to success folder and write new row to results csv file:
        else:
            os.replace(documents_paths[i], os.path.join(success_folder, os.path.basename(documents_paths[i])))
            number_success += 1
        print(document_ocr)

#Close the results csv file:
results.close()
print("Process finished with " + str(number_success) + " successes and " + str(number_failure) + " failures.")