import pygame

pygame.mixer.init()
pygame.mixer.music.load("chime-alert-demo-309545.mp3")
pygame.mixer.music.play()

# Wait long enough to hear the sound
import time
time.sleep(2)
