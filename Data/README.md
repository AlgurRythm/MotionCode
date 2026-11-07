# MotionCode Studio Advanced

## Install
1. Extract this folder.
2. Run `install_requirements.bat` once.
3. Run `run_motioncode.bat` to launch MotionCode.

## Startup compatibility fix
The application now exposes scene objects created in `build(scene)` as safe script globals before calling `animate(scene, t)`. This supports common scripts that create an object named `Title` and then refer to `title` inside `animate()`.

The original MotionCode editor/preview/timeline/object inspector layout is retained. The scene engine supports 2D primitives, custom polygons, images, wireframe 3D primitives, and Wavefront OBJ imports.

OBJ meshes are currently drawn as wireframes; this is not a full solid-material renderer.

Only run scripts you trust: MotionCode executes Python scripts locally.
