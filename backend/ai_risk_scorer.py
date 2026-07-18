import numpy as np
import pickle
import os
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

MODEL_PATH = 'risk_mlp_model.pkl'
SCALER_PATH = 'risk_scaler.pkl'

def generate_expert_data(n_samples=5000):
    np.random.seed(42)
    
    # Features: anomaly_score, max_dim_score, total_rules, high_sev_count
    anomaly_scores = np.random.uniform(0.0, 1.0, n_samples)
    max_dim_scores = np.random.uniform(0.0, 1.0, n_samples)
    total_rules = np.random.poisson(2, n_samples)
    high_sev_counts = np.array([np.random.binomial(n, 0.4) if n > 0 else 0 for n in total_rules])
    
    X = np.column_stack((anomaly_scores, max_dim_scores, total_rules, high_sev_counts))
    
    # Expert formula (representing non-linear interactions we want the AI to learn)
    y = np.zeros(n_samples)
    for i in range(n_samples):
        # Start with a base blend
        base = max_dim_scores[i] * 0.7 + anomaly_scores[i] * 0.3
        
        # Non-linear boost for high severity rules
        if high_sev_counts[i] >= 2:
            base += 0.3
        elif high_sev_counts[i] == 1:
            base += 0.15
            
        # Synergy between high anomaly and presence of rules
        if anomaly_scores[i] > 0.75 and total_rules[i] > 0:
            base += 0.2
            
        # Strict volume constraints requested by user: don't flag as high risk if very few rules triggered
        if total_rules[i] <= 1:
            base = min(base, 0.15)
        elif total_rules[i] == 2:
            base = min(base, 0.35) # Guarantee Low Risk for 2 rules
        elif total_rules[i] == 3:
            base = min(base, 0.65) # Guarantee Medium Risk for 3 rules
        elif total_rules[i] == 4:
            base = min(base, 0.88) # Allow High Risk for 4 rules
            
        y[i] = min(base, 1.0)
        
    return X, y

def train_and_save_model():
    X, y = generate_expert_data(10000)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train Multi-Layer Perceptron (Neural Network)
    mlp = MLPRegressor(
        hidden_layer_sizes=(16, 8), 
        activation='relu', 
        solver='adam', 
        max_iter=1000, 
        random_state=42
    )
    mlp.fit(X_scaled, y)
    
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(mlp, f)
    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
        
    print("AI Risk Scoring Model (Neural Network) trained and saved.")

def predict_risk(anomaly_score, max_dim_score, total_rules, high_sev_count):
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        train_and_save_model()
        
    with open(MODEL_PATH, 'rb') as f:
        mlp = pickle.load(f)
    with open(SCALER_PATH, 'rb') as f:
        scaler = pickle.load(f)
        
    X = np.array([[anomaly_score, max_dim_score, total_rules, high_sev_count]])
    X_scaled = scaler.transform(X)
    
    # Predict and constrain between 0 and 1
    pred = mlp.predict(X_scaled)[0]
    pred = min(max(float(pred), 0.0), 1.0)
    
    # Enforce strict volume constraints post-prediction to prevent AI smoothing
    if total_rules <= 1:
        pred = min(pred, 0.15)
    elif total_rules == 2:
        pred = min(pred, 0.35)
    elif total_rules == 3:
        pred = min(pred, 0.65)
    elif total_rules == 4:
        pred = min(pred, 0.88)
        
    return pred

if __name__ == "__main__":
    train_and_save_model()
