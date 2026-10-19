# SPDX-License-Identifier: GPL-3.0-only
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from backend import Connection, StageError, covers

class GuardTests(unittest.TestCase):
    def connection(self, **changes):
        c=Connection.__new__(Connection)
        c.fd=10;c.wfd=11;c.writes=0;c.jump_active=False;c.last_feature_tick={};c.log=lambda *x:None
        c.modules={'tomb123.exe':0x100000,'tomb1.dll':0x200000}
        c.maps=[{'start':0x200000,'end':0x700000,'perms':'rw-p'}]
        s=dict(ready=True,module='tomb1.dll',level=0,lara='0x300000',oxygen=500,health=955,room=1,vertical_speed=0,writes=0)
        s.update(changes);c.snapshot=lambda:s.copy()
        reads={'GameVersion':0,'Level':0,'MainPlayerEntity':0x300000}
        c.read=lambda a,f:next(v for k,v in reads.items() if a==c.addr('tomb123.exe' if k!='MainPlayerEntity' else 'tomb1.dll',k))
        return c
    @patch('backend.os.pwrite',return_value=2)
    def test_oxygen_writes_only_expected_field(self, write):
        c=self.connection();c.tick(True)
        write.assert_called_once_with(11,b'l\x07',c.addr('tomb1.dll','PlayerOxygen'))
    @patch('backend.os.pwrite')
    @patch('backend.os.close')
    def test_disabled_releases_write_descriptor(self, close, write):
        c=self.connection();c.tick(False)
        write.assert_not_called();close.assert_called_once_with(11);self.assertIsNone(c.wfd)
    @patch('backend.os.pwrite')
    def test_loading_or_dead_lara_never_writes(self, write):
        c=self.connection(ready=False);c.wfd=None;c.tick(True);write.assert_not_called()
    @patch('backend.os.pwrite')
    def test_transition_recheck_blocks_write(self, write):
        c=self.connection();c.read=lambda *a:2;c.tick(True);write.assert_not_called()
    @patch('backend.os.pwrite')
    def test_unwritable_field_fails_closed(self, write):
        c=self.connection();c.maps=[]
        with self.assertRaises(StageError):c.tick(True)
        write.assert_not_called()
    @patch('backend.os.pwrite')
    def test_unsupported_state_cannot_write(self, write):
        c=self.connection()
        def unsupported():raise StageError('unsupported build','bad hash')
        c.snapshot=unsupported
        with self.assertRaises(StageError):c.tick(True)
        write.assert_not_called()
    @patch('backend.os.pwrite',return_value=2)
    def test_health_and_fall_are_separate_features(self, write):
        c=self.connection(room=0,vertical_speed=180)
        c.tick({'infinite-health':True,'no-fall-damage':True})
        self.assertEqual(write.call_count,2)
        self.assertEqual(write.call_args_list[0].args,(11,b'\xd0\x07',0x300026))
        self.assertEqual(write.call_args_list[1].args,(11,b'\x82\x00',0x300024))
    @patch('backend.os.pwrite')
    def test_no_fall_does_not_change_swimming(self, write):
        c=self.connection(room=1,vertical_speed=180);c.tick({'no-fall-damage':True});write.assert_not_called()
    @patch('backend.os.pwrite',return_value=2)
    def test_jump_boost_uses_only_vertical_speed(self, write):
        c=self.connection(room=0,vertical_speed=-160);c.jump_active=True
        c.tick({'super-jump':True})
        write.assert_called_once_with(11,b'\x51\xff',0x300024)
        self.assertFalse(c.jump_active)
    @patch('backend.os.pwrite')
    def test_disabled_jump_clears_pending_boost(self, write):
        c=self.connection(room=0,vertical_speed=-100);c.wfd=None;c.jump_active=True
        c.tick({'infinite-oxygen':False,'super-jump':False})
        self.assertFalse(c.jump_active);write.assert_not_called()
    def test_bounds_require_entire_write_to_fit(self):
        m=[dict(start=100,end=102,perms='rw-p')]
        self.assertTrue(covers(m,100,2,'w'));self.assertFalse(covers(m,101,2,'w'))

if __name__=='__main__':unittest.main()
