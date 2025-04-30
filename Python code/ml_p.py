import numpy as np
import pandas as pd
import os
import cv2
import mediapipe as mp
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
import tensorflow as tf
import serial
import time

# Connect to NodeMCU (update COM port if needed)
ser = serial.Serial('COM3', 9600, timeout=1)  # <<== Make sure COM3 is your correct port
time.sleep(2)

MODEL_PATH = "C:\\Users\\singh\\OneDrive\\Desktop\\my_project\\conected codes\\sign_language_cnn_model.h5"

# ✅ Check if model already exists
if not os.path.exists(MODEL_PATH):
    print("Model not found. Training new model...")

    # 📦 Load Dataset
    data = pd.read_csv("C:\\Users\\singh\\.cache\\kagglehub\\datasets\\datamunge\\sign-language-mnist\\versions\\1\\sign_mnist_train.csv")  # Update with your actual CSV file name

    # ✂️ Split features and labels
    X = data.drop('label', axis=1).values / 255.0
    y = data['label'].values

    X = X.reshape(-1, 28, 28, 1)

    # 🧠 Encode labels
    encoder = LabelBinarizer()
    y = encoder.fit_transform(y)

    # 🔀 Train/Validation Split (80/20)
    x_train, x_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # 🧱 Build CNN Model
    model = Sequential([
        Conv2D(32, (3,3), activation='relu', input_shape=(28,28,1)),
        MaxPooling2D((2,2)),
        Conv2D(64, (3,3), activation='relu'),
        MaxPooling2D((2,2)),
        Conv2D(128,(3,3),activation='relu'),
        MaxPooling2D((2,2)),
        Flatten(),
        Dense(256, activation='relu'),
        Dense(24, activation='softmax')  # 24 classes (A–Z without J and Z)
    ])

    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    # 🏋️ Train Model
    history = model.fit(x_train, y_train, epochs=10, validation_data=(x_val, y_val), batch_size=16)

    # 💾 Save Model
    model.save(MODEL_PATH)

    # 📈 Plot Accuracy
    plt.plot(history.history['accuracy'], label='Train')
    plt.plot(history.history['val_accuracy'], label='Val')
    plt.legend()
    plt.title("Model Accuracy")
    plt.show()

else:
    print("Model found. Skipping training...")

# ✅ Load Model
model = load_model(MODEL_PATH)

# 🏷️ Label Map: A–Z without J
labels = [chr(i) for i in range(65, 91)]
labels.remove('J')  # J not present in dataset

# 🖐️ MediaPipe Hand Detection
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

def preprocess_hand(frame, bbox):
    x, y, w, h = bbox
    hand = frame[y:y+h, x:x+w]
    hand = cv2.cvtColor(hand, cv2.COLOR_BGR2GRAY)
    hand = cv2.resize(hand, (28, 28))
    hand = hand / 255.0
    return hand.reshape(-1, 28, 28, 1)

def predict_hand_sign(img_array):
    pred = model.predict(img_array, verbose=0)
    idx = np.argmax(pred)
    return labels[idx]

# 🎥 Webcam Live Prediction
cap = cv2.VideoCapture(0)
print("Webcam started. Show your sign. Press 'c' to capture, 'n' to send word, 'q' to quit.")

current_word = ""
last_prediction = None
prediction_counter = 0
stable_prediction = None

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            x_list = [lm.x for lm in hand_landmarks.landmark]
            y_list = [lm.y for lm in hand_landmarks.landmark]

            xmin = int(min(x_list) * w) - 20
            xmax = int(max(x_list) * w) + 20
            ymin = int(min(y_list) * h) - 20
            ymax = int(max(y_list) * h) + 20

            xmin, ymin = max(0, xmin), max(0, ymin)
            xmax = min(w, xmax)
            ymax = min(h, ymax)

            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)

            hand_img = preprocess_hand(frame, (xmin, ymin, xmax - xmin, ymax - ymin))
            current_prediction = predict_hand_sign(hand_img)

            if last_prediction == current_prediction:
                prediction_counter += 1
            else:
                prediction_counter = 0

            if prediction_counter > 5:  # If stable for 5 frames
                stable_prediction = current_prediction
            last_prediction = current_prediction

            if stable_prediction:
                cv2.putText(frame, f'Letter: {stable_prediction}', (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 255), 2)

    # Display current assembled word
    cv2.putText(frame, f'Word: {current_word}', (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    cv2.imshow("Sign Language Recognition", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('c'):
        if stable_prediction:
            current_word += stable_prediction
            print(f"Added: {stable_prediction} --> Current word: {current_word}")

    elif key == ord('n'):
        if current_word != "":
            ser.write((current_word + '\n').encode())
            print(f"Sent word to NodeMCU: {current_word}")
            current_word = ""  # Reset after sending

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
ser.close()
