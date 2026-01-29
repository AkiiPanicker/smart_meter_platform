import numpy as np
import pandas as pd
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import os
import json
from app.models import MeterReading, AIPrediction

class PredictiveModel:
    def __init__(self, model_path='app/lstm_classifier.h5', data_path='sensor_logs.json'):
        self.model_path = model_path
        self.data_path = data_path
        self.scaler = StandardScaler()
        self.TIME_STEPS = 10
        self.n_features = 3 # voltage, current, light
        self.model = self._load_or_train_model()

    def _load_data(self):
        """Loads and preprocesses data from the JSON log file."""
        if not os.path.exists(self.data_path):
            print(f"Data file not found at {self.data_path}. Cannot train model.")
            return None, None
        
        with open(self.data_path, 'r') as f:
            data = json.load(f)
            
        df = pd.DataFrame(data)
        if 'timestamp' not in df.columns or 'tamperFlag' not in df.columns:
            print("Data file is missing required columns ('timestamp', 'tamperFlag').")
            return None, None
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        features = df[['voltage', 'current', 'lightIntensity']]
        labels = df['tamperFlag']
        
        scaled_features = self.scaler.fit_transform(features)
        
        return scaled_features, labels.values

    def _create_sequences(self, features, labels):
        """Creates sequences for the LSTM classifier."""
        X, y = [], []
        for i in range(len(features) - self.TIME_STEPS):
            X.append(features[i:(i + self.TIME_STEPS)])
            # Label is 1 if any tamper event occurred in the sequence
            y.append(1 if np.any(labels[i:(i + self.TIME_STEPS)]) else 0)
        return np.array(X), np.array(y)

    def _build_model(self):
        """Builds the LSTM Classifier model."""
        inputs = Input(shape=(self.TIME_STEPS, self.n_features))
        x = LSTM(64, return_sequences=True)(inputs)
        x = Dropout(0.2)(x)
        x = LSTM(32, return_sequences=False)(x)
        x = Dropout(0.2)(x)
        x = Dense(16, activation='relu')(x)
        outputs = Dense(1, activation='sigmoid')(x)
        
        model = Model(inputs, outputs)
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model

    def _load_or_train_model(self):
        """Loads a pre-trained model or trains a new one if not found."""
        features, labels = self._load_data() # Always load data to fit the scaler
        if features is None or labels is None:
            print("Failed to load data, cannot initialize model.")
            return None

        if os.path.exists(self.model_path):
            print("Loading pre-trained AI classifier model...")
            return load_model(self.model_path) # safe_mode=False is often not needed with Keras 3 and .h5
        else:
            print("No pre-trained classifier found. Training a new one...")
            
            X, y = self._create_sequences(features, labels)
            
            if len(X) == 0:
                print("Not enough data to create sequences for training.")
                return None
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            model = self._build_model()
            model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_test, y_test), verbose=1)
            model.save(self.model_path)
            print(f"Classifier model trained and saved to {self.model_path}")
            return model

    def get_health_score_and_prediction(self, node_id: str, recent_readings: list):
        """
        Analyzes recent readings for a node to predict tampering and calculate a health score.
        """
        if self.model is None or len(recent_readings) < self.TIME_STEPS:
            return {"health_score": 100, "prediction": None}

        df = pd.DataFrame([r.__dict__ for r in recent_readings])
        df = df.sort_values('timestamp', ascending=False).head(self.TIME_STEPS)

        if len(df) < self.TIME_STEPS:
            return {"health_score": 100, "prediction": None}
            
        features = df[['voltage', 'current', 'light']].rename(columns={'light': 'lightIntensity'})
        # Use the already fitted scaler
        scaled_features = self.scaler.transform(features)
        sequence = np.array([scaled_features])
        
        tamper_probability = self.model.predict(sequence)[0][0]
        
        confidence = tamper_probability * 100
        health_score = 100 - confidence
        
        prediction = None
        # Create a prediction if confidence is above a certain threshold (e.g., 50%)
        if confidence > 50:
            severity = 'high' if confidence > 85 else 'medium'
            explanation = f"Predictive Alert: Model predicts a {confidence:.1f}% probability of a tamper event based on recent sensor patterns."
            
            prediction = AIPrediction(
                timestamp=pd.Timestamp.now().isoformat(),
                node_id=node_id,
                event_type="PREDICTED_TAMPER",
                confidence=confidence,
                explanation=explanation,
                severity=severity
            )
            
        return {
            "health_score": round(health_score),
            "prediction": prediction
        }