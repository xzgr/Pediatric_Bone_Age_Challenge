#!/usr/bin/python3

from six.moves import cPickle
import cv2
import fnmatch
import numpy as np
import os
import pandas as pd
import sys


# Cut the hand of the image
# Como la nueva imagen tien los colores de la mano mas resaltaos crea otra mascara,
# (imagen en blanco y negro)
# Busca los objetos mas grandes y los recorta de ambas,
# (de la original y de las mascara) es decir deja solo la mano,
# luego aplica la mascara a  la foto recortada.
#
def cutHand(image):
    imageOriginal = image.copy()

    # convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if (cv2.mean(gray)[0] > 50.0):
        imageOriginal = whitePatch(image)
        gray = cv2.cvtColor(imageOriginal, cv2.COLOR_BGR2GRAY)

    # applying gaussian blur
    blurred = cv2.GaussianBlur(gray, (47, 47), 0)

    # Dejar solo el color blanco, que fue el color que pintamos el objeto
    mask = cv2.inRange(
        blurred,
        np.array([100]),  # lower color
        np.array([255])  # upper color
    )
    # img_mask = cv2.bitwise_and(blurred, blurred, mask=mask)
    # blurred = cv2.GaussianBlur(img_mask, (45, 45), 0)

    # thresholdin: Otsu's Binarization method
    # _, thresh = cv2.threshold(mask, 100, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    thresh = cv2.GaussianBlur(mask, (51, 51), 0)

    (image, contours, _) = cv2.findContours(
        thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    # Supongo que el objeto mas grande las la mano o el único objeto en la imagen
    # De las lista de contornos buscar el índice del objeto mas grande
    objetoMasGrande = 0
    for i, cnt in enumerate(contours):
        if len(contours[objetoMasGrande]) < len(cnt):
            objetoMasGrande = i

    # create bounding rectangle around the contour (can skip below two lines)
    [x, y, w, h] = cv2.boundingRect(contours[objetoMasGrande])
    # Fondeo negro debajo de el objeto mas grande
    cv2.rectangle(image, (x, y), (x+w, y+h), (0, 0, 0), -1)

    cv2.drawContours(
        image,  # image,
        contours,  # objects
        objetoMasGrande,  # índice de objeto (-1, todos)
        (255, 255, 255),  # color
        -1  # tamaño del borde (-1, pintar adentro)
    )

    # Recortar ese ojeto
    mask = image[y:y+h, x:x+w]
    imageOriginal = imageOriginal[y:y+h, x:x+w]

    output = cv2.bitwise_and(imageOriginal, imageOriginal, mask=mask)

    # =============== Solo para ver imágenes ===================
    # show the images
    cv2.imwrite(
        os.path.join(__location__, "dataset_sample", "render", imgFile),
        np.hstack([
            imageOriginal,
            output
        ])
    )
    # =========================================================

    # En caso que la imagen quede negra devuelvo la original
    gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
    if (cv2.mean(gray)[0] <= 10.0):
        return imageOriginal
    else:
        return output


# white-patch, normaliza la los colores de la imagen
#
# Como las imágenes tiene diferentes tonalidades de colores
# Este algoritmo whit-patch pretende llevar los colores de la
# imágenes a un tono igual
def whitePatch(image):
    B, G, R = cv2.split(image)

    red = cv2.equalizeHist(R)
    green = cv2.equalizeHist(G)
    blue = cv2.equalizeHist(B)

    imgOut = cv2.merge((blue, green, red))

    return imgOut


# Create a mask for the hand.
# I guess the biggest object is the hand
#
def createMask(image):
    # Aplico una técnica para normalizar los colores general de la imagen
    imgColorEqualize = whitePatch(image)
    gray = cv2.cvtColor(imgColorEqualize, cv2.COLOR_BGR2GRAY)

    # Difuminamos la imagen para evitar borrar bordes
    mask = cv2.GaussianBlur(gray, (25, 25), 0)

    # Dejamos los grises más cerca del color blanco
    mask = cv2.inRange(
        mask,
        np.array(125),  # lower color
        np.array(255)  # upper color
    )

    # Crear un kernel de '1' de 20x20, usado como goma de borrar
    # kernel = np.ones((5, 5), np.uint8)

    # Se aplica la transformación: Opening
    # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # A la imagen se le aplica la primera mascara, obtengo una imagen mas limpiar
    # image = cv2.bitwise_and(image, image, mask=mask)

    # Convertimos a escala de grises
    # img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # image = cv2.bitwise_or(imgColorEqualize, image)
    image = cv2.bitwise_and(imgColorEqualize, imgColorEqualize, mask=mask)

    # Detectamos los bordes con Canny
    # img = cv2.Canny(image, 100, 400)  # 50,150  ; 100,500
    # img = cv2.Canny(image, 100, 400, apertureSize=3)
    img = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)

    # Buscamos los contornos
    (_, contours, _) = cv2.findContours(
        img,
        #            cv2.RETR_EXTERNAL,
        cv2.RETR_TREE,
        #            cv2.CHAIN_APPROX_SIMPLE
        cv2.CHAIN_APPROX_NONE
    )

    # print(len(contours))
    if len(contours) > 1:
        # Supongo que el objeto mas grande las la mano o el único objeto en la imagen
        # De las lista de contornos buscar el índice del objeto mas grande
        objetoMasGrande = 0
        for i, cnt in enumerate(contours):
            if cv2.contourArea(contours[objetoMasGrande]) < cv2.contourArea(cnt):
                objetoMasGrande = i

        # Pintar los objetos mas chichos que el 30% del grande, limite: (0.2, 0.5]
        lenOfObjetoGrande = cv2.contourArea(contours[objetoMasGrande]) * 0.3
        for i, cnt in enumerate(contours):
            # print(cv2.contourArea(cnt), lenOfObjetoGrande)
            if cv2.contourArea(cnt) < lenOfObjetoGrande:
                cv2.drawContours(image, contours, i, (0, 0, 0), -1)

        cv2.drawContours(
            image,  # image,
            contours,  # objects
            objetoMasGrande,  # índice de objeto (-1, todos)
            (255, 255, 255),  # color
            -1  # tamaño del borde (-1, pintar adentro)
        )

        # Difuminamos la imagen para evitar borrar bordes
        image = cv2.GaussianBlur(image, (25, 25), 0)

        image = cv2.cvtColor(whitePatch(image), cv2.COLOR_BGR2GRAY)

        # Dejar solo el color blanco, que fue el color que pintamos el objeto
        image = cv2.inRange(
            image,
            # np.array([60, 60, 60]),  # lower color
            np.array(70),  # lower color
            np.array(255)  # upper color
        )

    else:
        # TODO ver bien este caso
        # En caso de no encontrar objeto, envió la imagen
        # image = cv2.bitwise_or(imgColorEqualize, image)
        image = imgColorEqualize

    return image


# Show a progress bar
def updateProgress(progress, tick='', total='', status='Loading...'):
    barLength = 45
    if isinstance(progress, int):
        progress = float(progress)
    if progress < 0:
        progress = 0
        status = "Waiting...\r\n"
    if progress >= 1:
        progress = 1
        status = "Completed loading data\r\n"
    block = int(round(barLength * progress))
    sys.stdout.write(str("\rImage: {0}/{1} [{2}] {3}% {4}").format(
        tick,
        total,
        str(("#" * block)) + str("." * (barLength - block)),
        round(progress * 100, 1), status))
    sys.stdout.flush()


# For this problem the validation and test data provided by the concerned authority did not have labels, so the training data was split into train, test and validation sets
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
train_dir = os.path.join(__location__, 'dataset_sample')

X_train = []
y_age = []
y_gender = []

df = pd.read_csv(os.path.join(train_dir, 'dataset_sample_labels.csv'))
a = df.values
m = a.shape[0]

print('Loading data set...')
# file names on train_dir
files = os.listdir(train_dir)
# filtter image file
files = [f for f in files if fnmatch.fnmatch(f, '*.png')]
totalFile = len(files)

for i in range(totalFile):
    imgFile = files[i]

    # Update the progress bar
    updateProgress(float(i / totalFile), (i+1), totalFile, imgFile)

    y_age.append(df.boneage[df.id == int(imgFile[:-4])].tolist()[0])
    a = df.male[df.id == int(imgFile[:-4])].tolist()[0]
    if a:
        y_gender.append(1)
    else:
        y_gender.append(0)

    img_path = os.path.join(train_dir, imgFile)
    img = cv2.imread(img_path)

    imgBGR2RGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    mask = createMask(imgBGR2RGB.copy())

    img = cv2.bitwise_and(imgBGR2RGB, imgBGR2RGB, mask=mask)
    # =====================================================================
    # show the images
    cv2.imwrite(
        # os.path.join(__location__, "dataset_sample", "render", imgFile),
        'mask.png',
        np.hstack([
            img
        ])
    )
    img = cutHand(img)

    # TODO: Dejar solo el area de la mano antes de redimencionar

    # Red mencionar las imágenes
    img = cv2.resize(img, (224, 224))

    x = np.asarray(img, dtype=np.uint8)
    X_train.append(x)

updateProgress(1, totalFile, totalFile, imgFile)

print('\nSaving data...')
# Save data
train_pkl = open('data.pkl', 'wb')
cPickle.dump(X_train, train_pkl, protocol=cPickle.HIGHEST_PROTOCOL)
train_pkl.close()

train_age_pkl = open('data_age.pkl', 'wb')
cPickle.dump(y_age, train_age_pkl, protocol=cPickle.HIGHEST_PROTOCOL)
train_age_pkl.close()

train_gender_pkl = open('data_gender.pkl', 'wb')
cPickle.dump(y_gender, train_gender_pkl, protocol=cPickle.HIGHEST_PROTOCOL)
train_gender_pkl.close()
print('\nCompleted saved data')
