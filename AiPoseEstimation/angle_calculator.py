import numpy as np  

def calculate_angle(a, b, c):
    """
    Üç nokta arasındaki açıyı hesaplar.
    a, b, c: (x, y) koordinatlarıdır.
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    ba = a - b
    bc = c - b
    
    cos_theta = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(cos_theta)  
    return np.degrees(angle)  
