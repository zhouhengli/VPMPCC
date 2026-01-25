# Install script for directory: /home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/home/ddrx/f1tenth_ws/install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/osuf1_common/msg" TYPE FILE FILES
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common/msg/MPC_metadata.msg"
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common/msg/MPC_prediction.msg"
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common/msg/MPC_trajectory.msg"
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common/msg/NPoint.msg"
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common/msg/NPointSet.msg"
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common/msg/ReachSets.msg"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/osuf1_common/cmake" TYPE FILE FILES "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/osuf1_common/catkin_generated/installspace/osuf1_common-msg-paths.cmake")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include" TYPE DIRECTORY FILES "/home/ddrx/f1tenth_ws/devel/include/osuf1_common")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/roseus/ros" TYPE DIRECTORY FILES "/home/ddrx/f1tenth_ws/devel/share/roseus/ros/osuf1_common")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/common-lisp/ros" TYPE DIRECTORY FILES "/home/ddrx/f1tenth_ws/devel/share/common-lisp/ros/osuf1_common")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/gennodejs/ros" TYPE DIRECTORY FILES "/home/ddrx/f1tenth_ws/devel/share/gennodejs/ros/osuf1_common")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  execute_process(COMMAND "/usr/bin/python3" -m compileall "/home/ddrx/f1tenth_ws/devel/lib/python3/dist-packages/osuf1_common")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/python3/dist-packages" TYPE DIRECTORY FILES "/home/ddrx/f1tenth_ws/devel/lib/python3/dist-packages/osuf1_common")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/osuf1_common/catkin_generated/installspace/osuf1_common.pc")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/osuf1_common/cmake" TYPE FILE FILES "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/osuf1_common/catkin_generated/installspace/osuf1_common-msg-extras.cmake")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/osuf1_common/cmake" TYPE FILE FILES
    "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/osuf1_common/catkin_generated/installspace/osuf1_commonConfig.cmake"
    "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/osuf1_common/catkin_generated/installspace/osuf1_commonConfig-version.cmake"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/osuf1_common" TYPE FILE FILES "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/osuf1_common/package.xml")
endif()

