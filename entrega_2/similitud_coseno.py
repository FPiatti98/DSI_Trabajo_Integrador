import numpy as np

def similitud_coseno(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

documento_1 = np.array([0.95, 0.10])
documento_2 = np.array([0.15, 0.95])
documento_3 = np.array([0.65, 0.40])
consulta = np.array([0.10, 0.98])

print("D1:", similitud_coseno(consulta, documento_1))
print("D2:", similitud_coseno(consulta, documento_2))
print("D3:", similitud_coseno(consulta, documento_3))