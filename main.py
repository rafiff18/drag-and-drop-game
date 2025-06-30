import cv2
from cvzone.HandTrackingModule import HandDetector
import cvzone
import numpy as np
import random
import time

# Inisialisasi kamera
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

# Detektor tangan
detector = HandDetector(detectionCon=0.8, maxHands=2) 

# --- Variabel & Pengaturan ---
colors = [(255, 0, 255), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)]
color_names = ["MAGENTA", "GREEN", "RED", "CYAN", "YELLOW"]
gameState = "Start"

# Kelas kotak drag yang disempurnakan
class DragRect:
    def __init__(self, posCenter, size=[100, 100], color=(255, 0, 255), color_index=0):
        self.posCenter = posCenter
        self.size = size
        self.color = color
        self.color_index = color_index
        # Atribut is_grabbed tetap ada untuk logika permainan, tapi tidak untuk visual
        self.is_grabbed = False

    def update(self, cursor):
        cx, cy = self.posCenter
        w, h = self.size
        if cx - w // 2 < cursor[0] < cx + w // 2 and cy - h // 2 < cursor[1] < cy + h // 2:
            self.posCenter = cursor
            self.is_grabbed = True
            return True 
        return False

    # --- METODE DRAW DIUBAH DI SINI ---
    def draw(self, img):
        cx, cy = self.posCenter
        w, h = self.size
        
        # Gambar kotak selalu dalam keadaan normal, tanpa mempedulikan status 'is_grabbed'
        cv2.rectangle(img, (cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2), self.color, cv2.FILLED)
        cvzone.cornerRect(img, (cx - w // 2, cy - h // 2, w, h), 20, rt=0)

# Kelas target zone
class TargetZone:
    def __init__(self, posCenter, size=[120, 120], color=(255, 0, 255), color_index=0):
        self.posCenter = posCenter
        self.size = size
        self.color = color
        self.color_index = color_index
        self.feedback_timer = 0
        self.feedback_color = (0, 0, 255) 

    def trigger_feedback(self):
        self.feedback_timer = 15 

    def draw(self, img):
        cx, cy = self.posCenter
        w, h = self.size
        
        if self.feedback_timer > 0:
            cv2.rectangle(img, (cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2), self.feedback_color, 3)
            self.feedback_timer -= 1
        else:
            cv2.rectangle(img, (cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2), self.color, 2)
        
        cvzone.putTextRect(img, color_names[self.color_index], (cx - 40, cy - 65), scale=1.5, thickness=2,
                           colorT=(255,255,255), colorR=self.color, font=cv2.FONT_HERSHEY_PLAIN, offset=10, border=1, colorB=(0,0,0))

# --- Fungsi untuk Reset Permainan ---
def reset_game():
    global rectList, targetList, score, start_time, game_duration, time_left, floating_texts
    rectList = []
    targetList = []
    
    target_positions = [[i * 250 + 150, 600] for i in range(5)]
    random.shuffle(target_positions)
    
    for i in range(5):
        color_idx = i % len(colors)
        rectList.append(DragRect([random.randint(150, 1100), 150], color=colors[color_idx], color_index=color_idx))
        targetList.append(TargetZone(target_positions[i], color=colors[color_idx], color_index=color_idx))
    
    score = 0
    game_duration = 60
    start_time = time.time()
    time_left = game_duration
    floating_texts = []

reset_game() 

while True:
    success, img = cap.read()
    if not success:
        break
    img = cv2.flip(img, 1)
    
    if gameState == "Start":
        cvzone.putTextRect(img, "Angkat Tangan untuk Mulai", (350, 360), scale=2, thickness=3, offset=20)
        cvzone.putTextRect(img, "Tekan 'Q' untuk Keluar", (450, 420), scale=2, thickness=3, offset=20)
        hands_start, _ = detector.findHands(img, flipType=False)
        if hands_start:
            gameState = "Playing"
            start_time = time.time()

    elif gameState == "GameOver":
        cvzone.putTextRect(img, f"GAME OVER!", (450, 300), scale=3, thickness=4, offset=20, colorR=(0,0,255))
        cvzone.putTextRect(img, f"Skor Akhir: {score}", (470, 380), scale=2, thickness=3, offset=20)
        cvzone.putTextRect(img, "Tekan 'R' untuk Main Lagi", (420, 440), scale=2, thickness=3, offset=20)

    elif gameState == "Playing":
        hands, img = detector.findHands(img)
        imgNew = np.zeros_like(img, np.uint8)

        for rect in rectList:
            rect.is_grabbed = False
            
        if hands:
            for hand in hands:
                lmList = hand['lmList']
                if len(lmList) >= 13:
                    l, _, _ = detector.findDistance(lmList[8][:2], lmList[12][:2], img)
                    if l < 40: 
                        cursor = lmList[8][:2]
                        for rect in rectList:
                            if rect.update(cursor):
                                break

        for target in targetList:
            target.draw(imgNew)
            
        for rect in rectList:
            rect.draw(imgNew)
            
        for rect in rectList[:]: 
            if not rect.is_grabbed:
                for target in targetList:
                    tx, ty = target.posCenter
                    tw, th = target.size
                    cx, cy = rect.posCenter
                    if (tx - tw // 2 < cx < tx + tw // 2 and ty - th // 2 < cy < ty + th // 2):
                        if rect.color_index == target.color_index:
                            score += 10
                            floating_texts.append({'text': '+10', 'pos': (cx, cy), 'timer': 30, 'color': (0, 255, 0)})
                            rectList.remove(rect)
                            new_color_idx = random.randint(0, len(colors) - 1)
                            rectList.append(DragRect([random.randint(100, 1180), 150], color=colors[new_color_idx], color_index=new_color_idx))
                        else:
                            rect.posCenter = [random.randint(100, 1180), 150] 
                            target.trigger_feedback()
                            floating_texts.append({'text': '-5', 'pos': (cx, cy), 'timer': 30, 'color': (0, 0, 255)})
                            score = max(0, score - 5)
                        break 
        
        out = img.copy()
        alpha = 0.4
        mask = imgNew.astype(bool)
        out[mask] = cv2.addWeighted(img, alpha, imgNew, 1 - alpha, 0)[mask]

        for ftext in floating_texts[:]:
            cv2.putText(out, ftext['text'], (ftext['pos'][0], ftext['pos'][1] - ftext['timer']), cv2.FONT_HERSHEY_SIMPLEX, 1.5, ftext['color'], 3)
            ftext['timer'] -= 1
            if ftext['timer'] <= 0:
                floating_texts.remove(ftext)

        elapsed_time = time.time() - start_time
        time_left = max(0, int(game_duration - elapsed_time))
        
        cvzone.putTextRect(out, f"Skor: {score}", (50, 50), scale=3, thickness=3, offset=15)
        cvzone.putTextRect(out, f"Waktu: {time_left}s", (1000, 50), scale=2, thickness=3, offset=10, colorR=(255,0,0))
        
        if time_left <= 0:
            gameState = "GameOver"

    cv2.imshow("Color Sorting Game", out if 'out' in locals() else img)
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break
    if key == ord('e') and (gameState == "GameOver" or gameState == "Start"):
        reset_game()
        gameState = "Playing"

cap.release()
cv2.destroyAllWindows()