import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestBallDevice(MpfTestCase):

    def __init__(self, test_map):
        super(TestBallDevice, self).__init__(test_map)
        self._captured = 0
        self._enter = -1
        self._missing = 0
        self._requesting = 0
        self._queue = False

    def getConfigFile(self):
        return 'test_ball_device.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_device/'


    def _missing_ball(self):
        self._missing += 1

    def test_ball_count_during_eject(self):
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)

        self._missing = 0

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil2.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)

        self.assertEquals(0, self._missing)
        self.advance_time_and_run(10000)
        self.advance_time_and_run(10000)
        self.assertEquals(1, self._missing)


    def _requesting_ball(self, balls, **kwargs):
        self._requesting += balls

    def test_ball_eject_failed(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        self._captured = 0

        # launcher should retry eject
        self.advance_time_and_run(10)
        # coil2.pulse.assert_called_twice_with()
        self.assertEquals(2, coil2.pulse.call_count)

        self.assertEquals(0, self._requesting)


        # it should not claim a ball which enters the target
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)

#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
        self.advance_time_and_run(10000)

    def test_ball_eject_timeout_and_late_confirm(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()
        self._missing = 0

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()
        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        # but not confirm. eject timeout = 6s
        self.advance_time_and_run(15)
        coil2.pulse.assert_called_once_with()

        # late confirm
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, self._requesting)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, self._captured)

    def test_ball_left_and_return_failure(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()
        self._missing = 0

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()
        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        # it comes back (before timeout)
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        # retry after timeout
        self.advance_time_and_run(4)
        # coil2.pulse.assert_called_twice_with()
        self.assertEquals(2, coil2.pulse.call_count)

        self.assertEquals(0, self._captured)

        # ball did not leave the launcher (it returned). target should capture
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, self._requesting)
        self.assertEquals(0, self._missing)
        self.assertEquals(1, self._captured)


    def test_ball_eject_timeout_and_ball_missing(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()
        self._missing = 0
        self._captured = 0
        self._enter = 0

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_test_target1_ball_enter', self._ball_enter)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()
        self.assertEquals(1, self._captured)

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)

        # but not confirm. eject timeout = 6s
        self.advance_time_and_run(15)
        coil2.pulse.assert_called_once_with()

        self.advance_time_and_run(30)

        self.assertEquals(0, self._requesting)
        self.assertEquals(1, self._missing)
        self.assertEquals(1, playfield.balls)

        self._missing = 0
        self._requesting = 0
        self._captured = 0

        # target1 captures a ball since the eject failed
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, playfield.balls)

        # and ejects it
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, playfield.balls)

        self._captured = 0


        # launcher captures a ball and should retry
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        # coil2.pulse.assert_called_twice_with()
        self.assertEquals(2, coil2.pulse.call_count)

        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, playfield.balls)

        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)


        # and reaches target which claims it
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)

        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, playfield.balls)


    def test_eject_successful_to_playfield(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        # ball passes diverter switch
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        #coil_diverter.disable.assert_called_once_with()
        assert not coil_diverter.enable.called

        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil3.pulse.assert_called_once_with()
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.balls)

        # a ball hits a playfield switch
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)


        self.assertEquals(1, playfield.balls)


    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        if new_balls < 0:
            raise Exception("Balls went negative")

        self._enter += new_balls

    def _captured_from_pf(self, balls, **kwargs):
        self._captured += balls


    def test_eject_successful_to_other_trough(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter', self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._enter = -1
        self._captured = 0
        self._missing = 0


        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)
        self._captured = -1

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        # ball passes diverter switch
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        assert not coil_diverter.disable.called

        self.assertEquals(-1, self._enter)
        self.assertEquals(-1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)


    def test_eject_to_pf_and_other_trough(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = -1

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)


        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        # ball passes diverter switch
        # first ball to trough. diverter should be enabled
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)

        # eject of launcher should be confirmed now and the trough should eject
        # coil1.pulse.assert_called_twice_with()
        self.assertEquals(2, coil1.pulse.call_count)
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called


        self.assertEquals(-1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        # coil1.pulse.assert_called_twice_with()
        # coil2.pulse.assert_called_twice_with()
        self.assertEquals(2, coil1.pulse.call_count)
        self.assertEquals(2, coil2.pulse.call_count)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball leaves launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)

        # ball passes diverter switch
        # second ball should not be diverted
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called


        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.balls)

        # coil1.pulse.assert_called_twice_with()
        # coil2.pulse.assert_called_twice_with()
        self.assertEquals(2, coil1.pulse.call_count)
        self.assertEquals(2, coil2.pulse.call_count)
        coil3.pulse.assert_called_once_with()
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.balls)

        # a ball hits a playfield switch
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)


        self.assertEquals(-1, self._captured)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._missing)


    def test_eject_ok_to_receive(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = -1

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEquals(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # request an ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # request a second ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called


        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)


        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # ball passes diverter switch
        # first ball to target1. diverter should be not enabled
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # target1 receives and should eject it right away
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.balls)


        # eject of launcher should be confirmed now and trough can eject
        # the next ball
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        coil3.pulse.assert_called_once_with()
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.balls)

        # launcher receives a ball but cannot send it to target1 because its busy
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        coil3.pulse.assert_called_once_with()


        self.assertEquals(-1, self._captured)
        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)


        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.balls)

        # wait for confirm
        self.advance_time_and_run(10)

        # launcher should now eject the second ball
        # coil1.pulse.assert_called_twice_with()
        # coil2.pulse.assert_called_twice_with()
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil3.pulse.assert_called_once_with()


        # ball leaves launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)


        # ball passes diverter switch
        # second ball should not be diverted
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called

        # target1 receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.balls)

        # coil1.pulse.assert_called_twice_with()
        # coil2.pulse.assert_called_twice_with()
        # coil3.pulse.assert_called_twice_with()
        self.assertEquals(1, coil1.pulse.call_count)
        self.assertEquals(1, coil2.pulse.call_count)
        self.assertEquals(2, coil3.pulse.call_count)

        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.balls)

        # wait for confirm
        self.advance_time_and_run(10)

        self.assertEquals(-1, self._captured)

        self.assertEquals(2, playfield.balls)
        self.assertEquals(0, self._missing)

        # check that timeout behave well
        self.advance_time_and_run(1000)

    def test_missing_ball_idle(self):
        coil1 = self.machine.coils['eject_coil1']
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the balls
        coil1.pulse = MagicMock()
        self.assertEquals(2, device1.balls)

        # steal a ball from trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        assert not coil1.pulse.called
        self.assertEquals(1, self._missing)
        self.assertEquals(0, self._captured)
        self.assertEquals(1, playfield.balls)

        # count should be on less and one ball missing
        self.assertEquals(1, device1.balls)

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.balls)

        # ball randomly reappears
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._missing)
        self.assertEquals(1, self._captured)


    def test_ball_entry_during_eject(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEquals(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # assume there are already two balls on the playfield
        playfield.balls = 2

        # request an ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called


        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # important: ball does not leave launcher here

        # ball passes diverter switch
        # second ball should not be diverted
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called

        # target1 receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.balls)

        # coil1.pulse.assert_called_twice_with()
        # coil2.pulse.assert_called_twice_with()
        # coil3.pulse.assert_called_twice_with()
        self.assertEquals(1, coil1.pulse.call_count)
        self.assertEquals(1, coil2.pulse.call_count)
        self.assertEquals(1, coil3.pulse.call_count)


        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.balls)

        # wait for confirm via timeout
        self.advance_time_and_run(10)

        # target captured one ball because it did not leave the launcher
        self.assertEquals(1, self._captured)

        # there is no new ball on the playfield because the ball is still in the launcher
        self.assertEquals(2, playfield.balls)
        self.assertEquals(0, self._missing)

        # ball disappears from launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        # eject times out
        self.advance_time_and_run(15)
        # ball goes missing and magically the playfield count is right again
        self.advance_time_and_run(40)
        self.assertEquals(1, self._missing)
        self.assertEquals(3, playfield.balls)

        # check that timeout behave well
        self.advance_time_and_run(1000)

    def _block_eject(self, queue, **kwargs):
        self._queue = queue
        queue.wait()

    def test_ball_entry_during_ball_requested(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()
        self.assertEquals(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # request ball
        target3.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)


        # in the meantime device4 receives a (drained) ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)
        self.assertEquals(1, self._captured)
        self._captured = 0


        # launcher receives but cannot ejects ball yet
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        # target 2 ejects to target 3
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.balls)

        # still no eject of launcher
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        # target 3 receives
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 1)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.balls)

        # launcher should eject
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        # ball passes diverter switch
        # first ball to trough. diverter should be enabled
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)



    def test_eject_attempt_blocking(self):
        # this test is a bit plastic. we hack get_additional_ball_capacity
        # the launcher device will try to do an eject while device4 is busy.
        # at the moment we cannot trigger this case but it may happen with
        # devices which wait before they eject
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        device4.get_additional_ball_capacity = lambda *args: 10

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()
        self.assertEquals(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # request ball
        target3.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)


        # in the meantime device4 receives a (drained) ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)
        self.assertEquals(1, self._captured)
        self._captured = 0


        # launcher receives but cannot ejects ball yet
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        # however launcher will try to eject because we hacked
        # get_additional_ball_capacity. device4 should block the eject

        # target 2 ejects to target 3
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.balls)

        # still no eject of launcher
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        # target 3 receives
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 1)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.balls)

        # launcher should eject
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        # ball passes diverter switch
        # first ball to trough. diverter should be enabled
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)


    def test_two_concurrent_eject_to_pf_with_no_balls(self):
        coil3 = self.machine.coils['eject_coil3']
        coil5 = self.machine.coils['eject_coil5']
        target1 = self.machine.ball_devices['test_target1']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)


        coil3.pulse = MagicMock()
        coil5.pulse = MagicMock()

        # add a ball to target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        # add a ball to target3
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 1)
        self.advance_time_and_run(1)

        self._captured = 0
        self._missing = 0

        # both should eject to pf
        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, target1.balls)
        self.assertEquals(1, target3.balls)

        coil3.pulse.assert_called_once_with()
        coil5.pulse.assert_called_once_with()
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        # add a ball to target3
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 0)
        self.advance_time_and_run(1)

        # a ball hits a playfield switch
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        # it should confirm only one device (no matter which one)
        self.assertEquals(1, playfield.balls)

        # second ball should be confirmed via timeout
        self.advance_time_and_run(10)
        self.assertEquals(2, playfield.balls)

        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)


    def test_unstable_switches(self):
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(0.4)
        # however, second switch is unstable
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(0.4)

        self.assertEquals(0, self._captured)
        self.assertEquals(0, device1.balls)
        self.assertEquals(0, playfield.balls)
        self.assertRaises(ValueError, device1._count_balls())

        # the the other one
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(0.4)
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(0.4)

        self.assertEquals(0, self._captured)
        self.assertEquals(0, device1.balls)
        self.assertEquals(0, playfield.balls)
        self.assertRaises(ValueError, device1._count_balls())

        self.advance_time_and_run(1)
        # but finally both are stable

        self.assertEquals(2, self._captured)
        self.assertEquals(2, device1.balls)
        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEquals(2, self._captured)
        self.assertEquals(2, device1.balls)
        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)
        self.assertEquals("idle", device1._state)

    def test_permanent_eject_failure(self):
        coil1 = self.machine.coils['eject_coil1']
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0
        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        self.assertEquals(2, device1.balls)
        assert not coil1.pulse.called

        # request ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        coil1.pulse = MagicMock()

        # timeout is 10s and max 3 retries
        # ball leaves (1st)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)

        # and comes back before timeout
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        # after the timeout it should retry
        self.advance_time_and_run(10)
        coil1.pulse.assert_called_once_with()
        coil1.pulse = MagicMock()


        # ball leaves (2nd) for more than timeout
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(11)
        self.assertEquals(1, device1.balls)

        # and comes back
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        # trough should retry nearly instantly
        self.advance_time_and_run(1)
        coil1.pulse.assert_called_once_with()
        coil1.pulse = MagicMock()


        # ball leaves (3rd)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)

        # and comes back before timeout
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        # after the timeout the device marks itself as broken and will give up
        self.advance_time_and_run(10)
        assert not coil1.pulse.called

        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals("eject_broken", device1._state)


    def test_request_loops(self):
        # nobody has a ball and we request one. then we add a ball in the chain
        trough = self.machine.ball_devices['test_trough']
        trough2 = self.machine.ball_devices['test_target2']
        launcher = self.machine.ball_devices['test_launcher']
        target1 = self.machine.ball_devices['test_target1']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # no initial balls
        # request ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        self.assertEquals(1, len(target1.ball_requests))
        # should not crash

        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # trough captures2 a ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)
        self._captured = 0

        self.assertEquals(0, len(target1.ball_requests))

        # trough2 eject
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)

        # ball enters launcher2
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 1)
        self.advance_time_and_run(1)


        # launcher2 eject
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        coil5.pulse.assert_called_once_with()
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 0)
        self.advance_time_and_run(1)


        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)


        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        coil5.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, trough.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, launcher.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        coil5.pulse.assert_called_once_with()


        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)

        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, target1.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil3.pulse.assert_called_once_with()
        coil4.pulse.assert_called_once_with()
        coil5.pulse.assert_called_once_with()


        self.assertEquals(0, playfield.balls)
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.advance_time_and_run(10)

        # TODO:
#        self.assertEquals("idle", launcher._state)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._captured)

    def test_unexpected_balls(self):
        launcher = self.machine.ball_devices['test_launcher']
        target1 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']

        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # launcher catches a random ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)
        self._captured = 0

        # trough2 eject
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)

        # ball enters target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)

        # target1 should put it to the playfield
        coil2.pulse.assert_called_once_with()
        coil3.pulse.assert_called_once_with()

        self.assertEquals(0, playfield.balls)
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.advance_time_and_run(10)

        self.assertEquals("idle", launcher._state)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._captured)

    def test_balls_in_device_on_boot(self):
        # The device without the home tag should eject the ball
        # The device with the home tag should not eject the ball

        target1 = self.machine.ball_devices['test_target1']
        target2 = self.machine.ball_devices['test_target2']

        assert 'home' not in target1.tags
        assert 'home' in target2.tags

        # Put balls in both devices
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch_target2", 1)

        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']

        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()

        self.advance_time_and_run(10)

        coil3.pulse.assert_called_once_with()
        assert not coil4.pulse.called

    def test_player_controlled_eject(self):
        # tests starting a game, ball ejects to launcher, player has to hit a
        # button to launch the ball

        trough_coil = self.machine.coils['eject_coil1']
        trough_coil.pulse = MagicMock()

        launcher_coil = self.machine.coils['eject_coil2']
        launcher_coil.pulse = MagicMock()

        # Start with some balls in the trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)

        self.advance_time_and_run(1)

        # Start a game
        self.machine.events.post('game_start')

        # Trough should eject the ball, switches should bounce around a bit
        # ball should end up in launcher
        trough_coil.pulse.assert_called_once_with()
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)

        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(.1)

        # Launcher should not fire yet
        assert not launcher_coil.pulse.called

        # player hits switch tagged with 'launch', ball should launch
        assert 'launch' in self.machine.switches['s_launch'].tags

        self.machine.switch_controller.process_switch("s_launch", 1)
        self.advance_time_and_run(1)

        launcher_coil.pulse.assert_called_once_with()








