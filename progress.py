from IPython.display import display
import ipywidgets as widgets
import time
import threading
from matplotlib import pyplot as plt
import numpy as np

phase_delay = 290e-9

# Real time monitoring and plotting function
def update(pp, n_avg, job, dfs, results, ax, l_modulous, l_phase):
    while results.is_processing():
        # Fetch results
        I, Q, iteration = results.fetch_all()
        theta = dfs*phase_delay*2*np.pi
        Ir = 1e4*(np.cos(theta)*I-np.sin(theta)*Q)
        Qr = 1e4*(np.sin(theta)*I+np.cos(theta)*Q)
        S = Ir + 1j * Qr
        R = 20*np.log10(np.abs(S))-25  # Amplitude
        phase = np.unwrap(np.angle(S))*180/np.pi  # Phase
        # Update plot
        l_modulous.set_ydata(R)
        rescale(ax[0],R)
        l_phase.set_ydata(phase)
        rescale(ax[1],phase)
        # Progress bar
        pp.update(iteration, n_avg)
        # Stop if requested
        if not pp.keeprunning:
            break
    job.halt()

# Real time monitoring and plotting function
def updateIQ(pp, n_avg, job, results, ax, l_I, l_Q):
    while results.is_processing():
        # Fetch results
        I, Q, iteration = results.fetch_all()
        # Update plot
        theta = config.resonator_IF*phase_delay*2*np.pi # TOF correction
        Ir = 1e4*(np.cos(theta)*I-np.sin(theta)*Q)
        Qr = 1e4*(np.sin(theta)*I+np.cos(theta)*Q)
        l_I.set_ydata(Ir)
        rescale(ax[0], Ir)
        l_Q.set_ydata(Qr)
        rescale(ax[1], Qr)
        # Progress bar
        pp.update(iteration, n_avg)
        # Stop if requested
        if not pp.keeprunning:
            break
    job.halt()

    
def rot(I,Q):
    theta = -292*np.pi/180
    return I*np.cos(theta)-Q*np.sin(theta) , I*np.sin(theta)+Q*np.cos(theta)


# Real time monitoring and plotting function
def updatehist(pp, n_avg, job, results, ax, l_IQ0, l_IQ1):
    while results.is_processing():
        # Fetch results
        I0, Q0, I1, Q1, iteration = results.fetch_all()
        # Update plot
        nm = min(len(I0),len(I1),len(Q0),len(Q1))
        I0r, Q0r = rot(I0[:nm]*1e4,Q0[:nm]*1e4)
        I1r, Q1r = rot(I1[:nm]*1e4,Q1[:nm]*1e4)
        l_IQ0.set_data(I0r,Q0r)
        l_IQ1.set_data(I1r,Q1r)
        # Progress bar
        pp.update(iteration, n_avg)
        # Stop if requested
        if not pp.keeprunning:
            break
    job.halt()    

def rescale(line):
    ax = line.axes
    data = line.get_ydata()
    ymin,ymax=ax.get_ylim()
    dmin = data.min()
    dmax = data.max()
    delta = dmax-dmin
    if dmin<ymin or dmax>ymax or delta>2*(ymax-ymin):
        ax.set_ylim(dmin-0.05*delta, dmax+0.05*delta)
        
class ProgressPlot(threading.Thread):
    """
    Real time plot to monitor a QM job
    """
    def __init__(self, job):
        """Create real time plot to monitor a QM job
            Parameter:
            job: a running QM job
        """ 
        super().__init__()
        self.progress = widgets.FloatProgress(value=0.0, min=0.0, max=1.0)
        self.progress_label = widgets.Label(value="??/??")
        self.button_abort = widgets.Button(description='Abort',)
        self.button_abort.on_click(self.abort_clicked)
        self.output = widgets.Output()
        self.abort = False
        self.job = job
        with plt.ioff():
            self.fig = plt.figure()
        self.plot_init(self.fig)
        self.show()
        self.start()

    def plot_init(self, fig):
        pass

    def plot_update(self):
        pass

    def show(self):
        display(self.fig.canvas,widgets.HBox([self.button_abort,self.progress,self.progress_label]),self.output)
        
    def abort_clicked(self, button):
        self.abort = True

    def run(self):
        while self.job.status=="pending":
            time.sleep(0.1)
            self.output.append_stdout(f"Position in queue {self.job.position_in_queue()} \r")
            if self.abort:
                self.job.cancel()
                self.output.append_stdout("Job has been canceled\n")
                return
        t0 = time.time()
        while self.job.status!="running" and self.job.status!="completed" :
            time.sleep(0.1)
            if time-time()-t0>2:
                self.output.append_stdout("Job has been canceled\n")
                return
        if self.job.status=="running":
            self.output.append_stdout("Job is running...               \n")
        while self.job.status=="running":
            time.sleep(0.1)
            self.plot_update()
            self.fig.canvas.draw_idle()
            if self.abort:
                self.job.halt()
                self.output.append_stdout("Job has been halted\n")
                return
        self.output.append_stdout("Job has finished                 \n")
        t0 = time.time()
        while self.job.status!="completed" :
            time.sleep(0.1)
            if time-time()-t0>2:
                break
        self.plot_update()
        self.fig.canvas.draw_idle()
        

