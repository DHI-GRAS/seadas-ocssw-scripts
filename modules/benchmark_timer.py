"""
Module which allows timing to be performed.
"""
import time

HOURS_PER_DAY = 24
MINS_PER_HOUR = 60
SECS_PER_DAY = 86400
SECS_PER_HOUR = 3600
SECS_PER_MIN = 60

#2345678901234567890123456789012345678901234567890123456789012345678901234567890

class BenchmarkTimer(object):
    """ A class for simple benchmark timing. """
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_time = None

    def end(self):
        """ Sets the end time of the timer. """
        if self.start_time:
            if not self.end_time:
                self.end_time = time.time()
                self.total_time = self.end_time - self.start_time
            else:
                raise BenchmarkTimerError("Timer already ended at {0}.".format(self.get_end_time_str()))
        else:
            raise BenchmarkTimerError("Timer must started before it can be ended.")

    def get_end_time_str(self):
        if self.end_time:
            return time.strftime('%Y-%m-%d, %H:%M:%S', time.localtime(self.end_time))
        else:
            raise BenchmarkTimerError("The End time has not been set.")

    def get_start_time_str(self):
        if self.start_time:
            return time.strftime('%Y-%m-%d, %H:%M:%S', time.localtime(self.start_time))
        else:
            raise BenchmarkTimerError("Timer not started yet.")

    def start(self):
        """ Sets the start time of the timer. """
        if not self.start_time:
            self.start_time = time.time()
        else:
            raise BenchmarkTimerError("Timer already started at {0}.".format(self.get_start_time_str()))

    def get_total_time(self):
        """ Returns the elapsed time. """
        if self.start_time:
            if self.end_time:
                return self.start_time - self.end_time
            else:
                raise BenchmarkTimerError("Total time not available, timer still running.")
        else:
            raise BenchmarkTimerError("Total time not available, timer not yet started.")

    def get_total_time_str(self):
        """ Returns the elapsed time. """
        if self.total_time:
            return self.__str__()
        else:
            if self.start_time:
                raise BenchmarkTimerError('Total time not available!  Timer still running.')
            else:
                raise BenchmarkTimerError('Total time not available!  Timer not started.')

    def __repr__(self):
        if self.end_time:
            return self.start_time, self.end_time, self.total_time
        elif self.start_time:
            return self.start_time
        else:
            raise BenchmarkTimerError('Timer is not started yet.')

    def __str__(self):
        if self.total_time:
            (days, secs) = divmod(self.total_time, SECS_PER_DAY)
            (hours, secs) = divmod(secs, SECS_PER_HOUR)
            (mins, secs) = divmod(secs, SECS_PER_MIN)
            if days > 0:
                return '{0} {1:02d}:{2:02d}:{3:06.3f}'.format(
                       int(days), int(hours), int(mins), secs)
            else:
                return '{0:02d}:{1:02d}:{2:06.3f}'.format(int(hours),
                                                             int(mins), secs)
        elif self.start_time:
            return 'Timer started at {0} is still running.'.format( 
                   time.strftime('%Y/%m/%d, %H:%M:%S',
                   time.localtime(self.start_time)))
        else:
            raise BenchmarkTimerError('Timer is not started yet.')

class BenchmarkTimerError(Exception):
    """ Exception class for the BenchmarkTimer. """
    def __init__(self, m):
        self.msg = m
    def __str__(self):
        return repr(self.msg)
