import SwiftUI
import AVFoundation

/// SwiftUI wrapper around an AVCaptureVideoPreviewLayer attached to a MultiCamSession.
/// Forwards normalized tap coordinates (0..1, top-left origin) up via `onTap`.
struct CameraPreviewView: UIViewRepresentable {
    let session: MultiCamSession
    let lens: CameraFrame.Lens
    var onTap: ((CGPoint) -> Void)? = nil

    func makeCoordinator() -> Coordinator { Coordinator(onTap: onTap) }

    func makeUIView(context: Context) -> PreviewUIView {
        let view = PreviewUIView()
        view.backgroundColor = .black
        view.previewLayer = session.makePreviewLayer(for: lens)
        let tap = UITapGestureRecognizer(target: context.coordinator,
                                         action: #selector(Coordinator.handleTap(_:)))
        view.addGestureRecognizer(tap)
        context.coordinator.view = view
        return view
    }

    func updateUIView(_ uiView: PreviewUIView, context: Context) {
        context.coordinator.onTap = onTap
        if uiView.previewLayer == nil {
            uiView.previewLayer = session.makePreviewLayer(for: lens)
        }
    }

    final class Coordinator: NSObject {
        weak var view: PreviewUIView?
        var onTap: ((CGPoint) -> Void)?

        init(onTap: ((CGPoint) -> Void)?) {
            self.onTap = onTap
        }

        @objc func handleTap(_ recognizer: UITapGestureRecognizer) {
            guard let view = view, let onTap = onTap else { return }
            let location = recognizer.location(in: view)
            let nx = max(0, min(1, location.x / max(1, view.bounds.width)))
            let ny = max(0, min(1, location.y / max(1, view.bounds.height)))
            onTap(CGPoint(x: nx, y: ny))
        }
    }

    final class PreviewUIView: UIView {
        var previewLayer: AVCaptureVideoPreviewLayer? {
            didSet {
                oldValue?.removeFromSuperlayer()
                if let l = previewLayer {
                    l.frame = bounds
                    layer.addSublayer(l)
                }
            }
        }

        override func layoutSubviews() {
            super.layoutSubviews()
            previewLayer?.frame = bounds
        }
    }
}
