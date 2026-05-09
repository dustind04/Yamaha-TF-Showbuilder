# ShowBuilder 3D

iOS app that uses the three rear cameras on iPhone Pro to capture a metric 3D
profile of an object and export it as STL.

## How it works

1. The app opens an `AVCaptureMultiCamSession` and streams synchronized frames
   from the ultra-wide, wide, and telephoto cameras at 720p / 30 fps.
2. The user taps two distinguishable reference points on the object (e.g. the
   centers of two holes) in the wide-camera preview and types in the real-world
   distance between them.
3. We auto-locate the same two points in the ultra-wide and telephoto frames by
   normalized cross-correlation patch matching, triangulate them via DLT in the
   rig's local frame, and use the user-supplied distance to set the global
   metric scale.
4. As the user sweeps the phone around the object, every fresh triplet of
   simultaneous frames is fed through Vision-based keypoint detection, NCC
   matching across the rig, and DLT triangulation again — producing a sparse
   metric point cloud in `PointCloud`.
5. When the user taps "Finish", the cloud is meshed into a 2.5D height field
   along its dominant plane (PCA + median binning + bilinear hole fill) and the
   triangle set is written out as a binary STL in the app's Documents
   directory. The SwiftUI `ShareLink` lets the user export it via the system
   share sheet.

The pipeline is designed so the user's two-point distance is the *only* metric
input the system needs — everything else (camera intrinsics, inter-camera
extrinsic translation, motion estimates) is rescaled by the calibration
factor.

## Hardware / OS requirements

- iPhone 11 Pro or later (any model supporting `AVCaptureMultiCamSession` and
  having all three rear lenses).
- iOS 16.0+ (deployment target in `project.yml`).
- Xcode 15+ on macOS.

`AVCaptureMultiCamSession.isMultiCamSupported` is checked at startup; the app
also runs with two of the three lenses if one is missing, falling back to a
two-view triangulation per frame.

## Why no ARKit?

`ARSession` and `AVCaptureMultiCamSession` are mutually exclusive on the back
cameras — only one can own the AV pipeline at a time. This app drives motion
estimation from `CMMotionManager` (orientation prior) and visual ego-motion is
left as an extension point in `Tracking/IMUPoseProvider.swift`. The two-point
calibration provides the absolute scale that IMU dead reckoning otherwise
lacks.

## Building

This repo ships an [XcodeGen](https://github.com/yonaskolb/XcodeGen) spec
(`project.yml`) instead of a checked-in `.xcodeproj`. To build:

```sh
brew install xcodegen
xcodegen generate
open ShowBuilder3D.xcodeproj
```

Set your Apple developer team in the target's signing settings, then run on a
real device (multi-cam is not supported in the iOS simulator).

## Source layout

```
ShowBuilder3D/
├── App/                       SwiftUI app entry, Info.plist
├── Capture/
│   ├── MultiCamSession.swift          AVCaptureMultiCamSession with 3 inputs
│   ├── CameraCalibration.swift        Pull intrinsics off CMSampleBuffers
│   └── SynchronizedFrame.swift        Frame triplet model
├── Tracking/
│   ├── Pose.swift                     Camera-to-world transform type
│   ├── IMUPoseProvider.swift          CoreMotion-based pose feed
│   └── FeatureTracker.swift           Vision keypoints + NCC matching
├── Geometry/
│   ├── CameraRig.swift                Per-lens K, wide-to-lens extrinsic
│   ├── Triangulation.swift            DLT, N-view triangulation + reprojection
│   ├── Calibration.swift              Two-point metric calibration
│   ├── PointCloud.swift               Voxel-deduplicated 3D point store
│   └── SurfaceReconstruction.swift    Height-field mesher + point markers
├── Export/
│   └── STLWriter.swift                Binary STL output
├── UI/
│   ├── ScanSession.swift              Workflow state machine + orchestration
│   ├── CameraPreviewView.swift        AVCaptureVideoPreviewLayer wrapper
│   └── RootView.swift                 SwiftUI top-level UI
└── Math/
    └── LinearAlgebra.swift            SVD via Accelerate, helpers
```

## Known limitations

- Per-frame triangulated points are added in that frame's local wide-camera
  coordinates. Without pose-tracked registration across frames, the cloud will
  smear if the phone moves significantly during a scan. The intended next step
  is a PnP-based pose solver (`Geometry/Triangulation.swift` already provides
  reprojection residuals, which a Levenberg–Marquardt PnP would consume).
- Inter-camera extrinsics use approximate factory baselines for iPhone Pro
  geometry. To use the manufacturer-calibrated values, attach an
  `AVCaptureDepthDataOutput` to the wide camera and read
  `AVCameraCalibrationData.extrinsicMatrix` (see TODO in `MultiCamSession`).
- Surface reconstruction is a 2.5D height field — adequate for sweep-style
  profile captures, not for closed objects. Plug in a Poisson or ball-pivoting
  reconstructor at `SurfaceReconstruction.mesh(from:method:)` for closed
  meshes.
- The Vision-based keypoint detector uses contour sampling as a placeholder.
  Replace with a proper Harris/FAST detector for production-grade density.

## STL units

Output STL coordinates are in **meters**. CAD/slicer tools that expect
millimeters should import with a 1000× scale factor.
