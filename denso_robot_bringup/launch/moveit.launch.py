from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition, UnlessCondition



def launch_setup(context, *args, **kwargs):

    model = LaunchConfiguration("model")
    namespace = LaunchConfiguration("namespace")
    simulation = LaunchConfiguration("simulation")
    ip_address = LaunchConfiguration("ip_address")

    send_format = LaunchConfiguration("send_format")
    recv_format = LaunchConfiguration("recv_format")
    verbose = LaunchConfiguration("verbose")
    control_cycle = LaunchConfiguration("bcap_slave_control_cycle_msec")

    robot_controller = LaunchConfiguration("robot_controller")

    moveit_pkg = FindPackageShare("denso_robot_moveit_config")
    desc_pkg = FindPackageShare("denso_robot_descriptions")

    # ---------------------------
    # URDF
    # ---------------------------

    robot_description = {
        "robot_description": Command(
            [
                "xacro ",
                PathJoinSubstitution(
                    [desc_pkg, "urdf", "denso_robot.urdf.xacro"]
                ),
                " model:=", model,
                " ip_address:=", ip_address,
                " namespace:=", namespace,
                " sim:=", simulation,
                " send_format:=", send_format,
                " recv_format:=", recv_format,
                " verbose:=", verbose,
            ]
        )
    }

    # ---------------------------
    # SRDF
    # ---------------------------

    robot_description_semantic = {
        "robot_description_semantic": Command(
            [
                "xacro ",
                PathJoinSubstitution(
                    [
                        moveit_pkg,
                        "robots",
                        model,
                        "srdf",
                        "denso_robot_macro.srdf.xacro",
                    ]
                ),
                " model:=", model,
                " namespace:=", namespace,
            ]
        )
    }

    # ---------------------------
    # MoveIt configs
    # ---------------------------

    kinematics_yaml = PathJoinSubstitution(
        [moveit_pkg, "config", "kinematics.yaml"]
    )

    ompl_yaml = PathJoinSubstitution(
        [moveit_pkg, "config", "ompl_planning.yaml"]
    )

    joint_limits_yaml = PathJoinSubstitution(
        [moveit_pkg, "robots", model, "config", "joint_limits.yaml"]
    )

    moveit_controllers_yaml = PathJoinSubstitution(
        [moveit_pkg, "robots", model, "config", "moveit_controllers.yaml"]
    )

    ros2_controllers_yaml = PathJoinSubstitution(
        [moveit_pkg, "robots", model, "config", "denso_robot_controllers.yaml"]
    )

    rviz_config = PathJoinSubstitution(
        [moveit_pkg, "rviz", "view_robot.rviz"]
    )

    # ---------------------------
    # Static TF
    # ---------------------------

    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=["--frame-id", "world", "--child-frame-id", "base_link"],
    )

    # ---------------------------
    # ros2_control
    # ---------------------------

    ros2_control = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            robot_description,
            ros2_controllers_yaml,
            {
                "denso_bcap_slave_control_cycle_msec": control_cycle,
            },
        ],
        output="screen",
    )

    # ---------------------------
    # Controller spawners
    # ---------------------------

    joint_state_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "denso_joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
    )

    trajectory_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            robot_controller,
            "--controller-manager",
            "/controller_manager",
        ],
    )

    # ---------------------------
    # Robot state publisher
    # ---------------------------

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[robot_description],
    )

    # ---------------------------
    # Move Group
    # ---------------------------

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,

            {"robot_description_kinematics": kinematics_yaml},
            {"robot_description_planning": joint_limits_yaml},

            {"planning_pipelines": ["ompl"]},
            {"planning_plugin": "ompl_interface/OMPLPlanner"},
            {"ompl": ompl_yaml},

            {"moveit_controller_manager":
            "moveit_simple_controller_manager/MoveItSimpleControllerManager"},

            moveit_controllers_yaml,
        ],
    )

    joint_state_pub = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
    )

    # ---------------------------
    # RViz
    # ---------------------------

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", rviz_config],
        parameters=[
            robot_description,
            robot_description_semantic,
            {"robot_description_kinematics": kinematics_yaml},
        ],
    )

    return [
        static_tf,
        ros2_control,
        joint_state_spawner,
        trajectory_spawner,
        robot_state_publisher,
        joint_state_pub,
        move_group,
        rviz,
    ]


def generate_launch_description():

    return LaunchDescription(
        [
            DeclareLaunchArgument("model"),
            DeclareLaunchArgument("namespace", default_value=""),
            DeclareLaunchArgument("simulation", default_value="true"),
            DeclareLaunchArgument("ip_address", default_value="192.168.0.1"),
            DeclareLaunchArgument("send_format", default_value="288"),
            DeclareLaunchArgument("recv_format", default_value="292"),
            DeclareLaunchArgument("verbose", default_value="false"),
            DeclareLaunchArgument(
                "bcap_slave_control_cycle_msec", default_value="8.0"
            ),
            DeclareLaunchArgument(
                "robot_controller",
                default_value="denso_joint_trajectory_controller",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )