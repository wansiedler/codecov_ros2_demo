# Copyright 2026 Alexander Paul Wansiedler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration test for the velocity limiter node.

The unit tests cover the limiting maths. This covers the part they cannot: that
the node declares its parameters, subscribes to cmd_vel_raw, applies the limiter
and republishes on cmd_vel.
"""

import time
import unittest

import launch
import launch_ros.actions
import launch_testing.actions
import launch_testing.markers
import pytest
import rclpy
from geometry_msgs.msg import Twist


@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():
    """Starts the node with limits the test can reason about."""
    node = launch_ros.actions.Node(
        package="nav_utils",
        executable="velocity_limiter_node",
        parameters=[
            {
                "max_linear": 0.5,
                "max_angular": 1.0,
                # High enough that the acceleration ramp never masks the clamp:
                # this test is about the wiring, the ramp has its own unit tests.
                "max_linear_accel": 1000.0,
            }
        ],
        output="screen",
    )
    return (
        launch.LaunchDescription([node, launch_testing.actions.ReadyToTest()]),
        {"velocity_limiter": node},
    )


class TestVelocityLimiterNode(unittest.TestCase):
    """Drives the node over real topics."""

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node("velocity_limiter_test_client")
        self.received = []
        self.publisher = self.node.create_publisher(Twist, "cmd_vel_raw", 10)
        self.subscription = self.node.create_subscription(
            Twist, "cmd_vel", self.received.append, 10
        )
        self._wait_for_node()

    def tearDown(self):
        self.node.destroy_node()

    def _wait_for_node(self, timeout=10.0):
        """Waits until the node under test is on both sides of the connection."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if (
                self.publisher.get_subscription_count() > 0
                and self.subscription.get_publisher_count() > 0
            ):
                return
        self.fail("velocity_limiter_node never connected to the test topics")

    def _send(self, linear, angular, timeout=5.0):
        """Publishes one command and returns the first reply."""
        self.received.clear()
        command = Twist()
        command.linear.x = linear
        command.angular.z = angular

        deadline = time.time() + timeout
        while time.time() < deadline:
            self.publisher.publish(command)
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if self.received:
                return self.received[0]
        self.fail(f"no reply on cmd_vel for linear={linear} angular={angular}")
        return None

    def test_passes_a_command_inside_the_limits(self):
        reply = self._send(0.2, 0.3)
        self.assertAlmostEqual(reply.linear.x, 0.2, places=6)
        self.assertAlmostEqual(reply.angular.z, 0.3, places=6)

    def test_clamps_a_command_above_the_limits(self):
        reply = self._send(5.0, 9.0)
        self.assertAlmostEqual(reply.linear.x, 0.5, places=6)
        self.assertAlmostEqual(reply.angular.z, 1.0, places=6)

    def test_clamps_a_reverse_command(self):
        reply = self._send(-5.0, -9.0)
        self.assertAlmostEqual(reply.linear.x, -0.5, places=6)
        self.assertAlmostEqual(reply.angular.z, -1.0, places=6)


@launch_testing.post_shutdown_test()
class TestNodeShutdown(unittest.TestCase):
    """The node has to exit cleanly, otherwise gcov never flushes its counters."""

    def test_exits_without_error(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
