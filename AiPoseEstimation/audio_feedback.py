from gtts import gTTS
import pygame

def play_audio_feedback(message):
    """ Yanlış yapılan hareketi sesli olarak anlatır """
    tts = gTTS(text=message, lang="tr")
    tts.save("alert.wav")  

    pygame.mixer.init()
    sound = pygame.mixer.Sound("alert.wav")
    sound.play()
