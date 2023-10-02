//
//  ContentView.swift
//  life-upgrade-hackathon Watch App
//
//  Created by Max Loeffler on 10/1/23.
//

import SwiftUI
import AVFoundation

struct RecordingView: View {
    @State private var audioRecorder: AVAudioRecorder?
    @State private var isRecording = false
    
    var body: some View {
        VStack {
            Button(action: {
                self.isRecording ? self.stopRecording() : self.startRecording()
                self.isRecording.toggle()
            }) {
                Text(isRecording ? "Stop Recording" : "Start Recording")
            }
        }
    }
    
    func startRecording() {
        let recordingSession = AVAudioSession.sharedInstance()
        try? recordingSession.setCategory(.playAndRecord, mode: .default)
        try? recordingSession.setActive(true)
        
        let audioFilename = getDocumentsDirectory().appendingPathComponent("recording.m4a")
        
        let settings = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 12000,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        audioRecorder = try? AVAudioRecorder(url: audioFilename, settings: settings)
        audioRecorder?.record()
    }
    
    func stopRecording() {
        audioRecorder?.stop()
        uploadRecording()
    }
    
    func getDocumentsDirectory() -> URL {
        let paths = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)
        return paths[0]
    }
    
    func uploadRecording() {
        let audioFilename = getDocumentsDirectory().appendingPathComponent("recording.m4a")
        let url = URL(string: "http://SERVER_IP:5000/upload")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var data = Data()
        data.append("\r\n--\(boundary)\r\n".data(using: .utf8)!)
        data.append("Content-Disposition: form-data; name=\"file\"; filename=\"recording.m4a\"\r\n".data(using: .utf8)!)
        data.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
        data.append(try! Data(contentsOf: audioFilename))
        data.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        
        let task = URLSession.shared.uploadTask(with: request, from: data) { responseData, response, error in
            // handle the response
            if let error = error {
                print("Failed to upload: \(error)")
            } else {
                print("Successfully uploaded")
                // Optionally print server response
                if let responseData = responseData, let responseString = String(data: responseData, encoding: .utf8) {
                    print("Server response: \(responseString)")
                }
            }
        }
        task.resume()
    }
}

struct RecordingView_Previews: PreviewProvider {
    static var previews: some View {
        RecordingView()
    }
}
