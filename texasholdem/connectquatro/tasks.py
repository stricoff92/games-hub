
import time

from texasholdem.celery_conf import app

@app.task
def cq_task(n):
    print("cq_task ============================ START")
    time.sleep(5)
    print("cq_task ============================ DONE")
