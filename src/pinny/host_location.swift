import AppKit
import CoreLocation
import Foundation

final class LocationFetcher: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private let outputPath: String?
    private var finished = false
    private(set) var exitCode: Int32 = 1

    init(outputPath: String? = nil) {
        self.outputPath = outputPath
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
    }

    func start() {
        guard CLLocationManager.locationServicesEnabled() else {
            finishFailure(code: "location_services_disabled")
            return
        }

        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .notDetermined:
            manager.startUpdatingLocation()
        case .restricted, .denied:
            finishFailure(code: "permission_denied")
        @unknown default:
            finishFailure(code: "unknown_authorization")
        }
    }

    func handleTimeout() {
        finishFailure(code: "timeout")
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .restricted, .denied:
            finishFailure(code: "permission_denied")
        case .notDetermined:
            break
        @unknown default:
            finishFailure(code: "unknown_authorization")
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else {
            finishFailure(code: "location_unavailable")
            return
        }
        finishSuccess(latitude: location.coordinate.latitude, longitude: location.coordinate.longitude)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        if let locationError = error as? CLError {
            switch locationError.code {
            case .denied:
                if manager.authorizationStatus == .notDetermined {
                    return
                }
                finishFailure(code: "permission_denied")
                return
            case .locationUnknown:
                return
            default:
                break
            }
        }
        finishFailure(code: "location_error", detail: error.localizedDescription)
    }

    private func finishSuccess(latitude: Double, longitude: Double) {
        guard !finished else { return }
        finished = true
        exitCode = 0
        emit(["latitude": latitude, "longitude": longitude])
        CFRunLoopStop(CFRunLoopGetMain())
    }

    private func finishFailure(code: String, detail: String? = nil) {
        guard !finished else { return }
        finished = true
        exitCode = 1
        var payload: [String: Any] = ["error": code]
        if let detail, !detail.isEmpty {
            payload["detail"] = detail
        }
        emit(payload)
        CFRunLoopStop(CFRunLoopGetMain())
    }

    private func emit(_ payload: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: payload, options: []) else {
            let fallback = "{\"error\":\"serialization_failed\"}\n"
            FileHandle.standardOutput.write(Data(fallback.utf8))
            return
        }
        if let outputPath {
            var outputData = data
            outputData.append(Data("\n".utf8))
            try? outputData.write(to: URL(fileURLWithPath: outputPath))
        }
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let fetcher = LocationFetcher(outputPath: CommandLine.arguments.dropFirst().first)
DispatchQueue.main.async {
    fetcher.start()
}
DispatchQueue.main.asyncAfter(deadline: .now() + 15) {
    fetcher.handleTimeout()
}
CFRunLoopRun()
exit(fetcher.exitCode)
