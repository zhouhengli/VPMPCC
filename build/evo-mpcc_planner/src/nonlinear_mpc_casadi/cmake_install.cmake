# Install script for directory: /home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/nonlinear_mpc_casadi

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
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/nonlinear_mpc_casadi/catkin_generated/installspace/nonlinear_mpc_casadi.pc")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/nonlinear_mpc_casadi/cmake" TYPE FILE FILES
    "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/nonlinear_mpc_casadi/catkin_generated/installspace/nonlinear_mpc_casadiConfig.cmake"
    "/home/ddrx/f1tenth_ws/build/evo-mpcc_planner/src/nonlinear_mpc_casadi/catkin_generated/installspace/nonlinear_mpc_casadiConfig-version.cmake"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/nonlinear_mpc_casadi" TYPE FILE FILES "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/nonlinear_mpc_casadi/package.xml")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/nonlinear_mpc_casadi" TYPE FILE FILES
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/nonlinear_mpc_casadi/scripts/Nonlinear_MPC.so"
    "/home/ddrx/f1tenth_ws/src/evo-mpcc_planner/src/nonlinear_mpc_casadi/scripts/Nonlinear_MPC_node.so"
    )
endif()

