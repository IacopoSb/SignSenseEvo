package com.chaquo.signSenseDEMO

import android.content.Intent
import android.graphics.Bitmap
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.util.concurrent.Callable
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.Future


// TODO
// - Setting ImageView To null doesnt free the Viewer from the last frame
// - Changing Progress Bar Visibility to VISIBLE doesnt show

class MainActivity : AppCompatActivity() {

    private lateinit var progressBar: ProgressBar
    private lateinit var handler: Handler
    private lateinit var speechRecognizer: SpeechRecognizer
    private var frameIndex = 0
    private var frames: List<Bitmap>? = null
    private val fps = 35.0
    private val frameInterval = (1000.0 / fps).toLong() // Interval in milliseconds
    private var lexiconPath = ""
    private var fingerspellingLexiconPath = ""
    private val width = 720  // Larghezza dei frame
    private val height = 720 // Altezza dei frame

    private fun copyAssetFolderToInternalStorage(assetFolderName: String): String {
        try {
            val assetFiles = assets.list(assetFolderName) ?: return ""
            val destFolder = File(filesDir, assetFolderName)
            if (!destFolder.exists()) {
                destFolder.mkdirs()
            }
            assetFiles.forEach { assetFile ->
                val assetPath = "$assetFolderName/$assetFile"
                val destFile = File(destFolder, assetFile)
                copyAssetToInternalStorage(assetPath, destFile)
            }
        } catch (e: Exception) {
            Log.e(
                "FilePaths",
                "Errore durante la copia della cartella $assetFolderName: ${e.message}"
            )
        }
        return "$filesDir/$assetFolderName"
    }

    private fun copyAssetToInternalStorage(assetFilePath: String, destFile: File) {
        try {
            assets.open(assetFilePath).use { inputStream ->
                FileOutputStream(destFile).use { outputStream ->
                    inputStream.copyTo(outputStream)
                }
            }
            Log.d("FilePaths", "$assetFilePath copiato in: ${destFile.absolutePath}")
        } catch (e: Exception) {
            Log.e("FilePaths", "Errore durante la copia del file $assetFilePath: ${e.message}")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        progressBar = findViewById<ProgressBar>(R.id.progressBar)
        progressBar.visibility = View.INVISIBLE

        // Avvio del modulo Python
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        lexiconPath = copyAssetFolderToInternalStorage("lexicon")
        fingerspellingLexiconPath = copyAssetFolderToInternalStorage("fingerspelling_lexicon")

        Log.d("FilePaths", lexiconPath)
        Log.d("FilePaths", fingerspellingLexiconPath)

        // Inizializza SpeechRecognizer
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}

            override fun onBeginningOfSpeech() {}

            override fun onRmsChanged(rmsdB: Float) {}

            override fun onBufferReceived(buffer: ByteArray?) {}

            override fun onEndOfSpeech() {}

            override fun onError(error: Int) {
                Toast.makeText(this@MainActivity, "Errore nella registrazione", Toast.LENGTH_SHORT)
                    .show()
            }

            override fun onResults(results: Bundle?) {
                val data = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val spokenText = data?.get(0) ?: ""
                Log.d("SpeechResult", spokenText)
                handleSpeechResult(spokenText)
            }

            override fun onPartialResults(partialResults: Bundle?) {}

            override fun onEvent(eventType: Int, params: Bundle?) {}
        })

        // Inizializza Button
        findViewById<Button>(R.id.button).setOnLongClickListener {
            startVoiceRecognition()
            true
        }
    }

    private fun startVoiceRecognition() {
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
            )
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "it-IT")  // Imposta la lingua italiana
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Parla ora")
            speechRecognizer.startListening(intent)
        } else {
            Toast.makeText(
                this,
                "Il servizio di riconoscimento vocale non è disponibile sul dispositivo",
                Toast.LENGTH_LONG
            ).show()
            Log.e("SpeechRecognizer", "Recognition service not available on this device.")
        }
    }
    private fun handleSpeechResult(text: String) {
        try {
            progressBar.visibility = View.VISIBLE

            val callStartTime = System.currentTimeMillis()
            val module = Python.getInstance().getModule("mainAndroid")
            val framesPyObject =
                module.callAttr("text_to_frames", text, lexiconPath, fingerspellingLexiconPath)
            val callEndTime = System.currentTimeMillis()
            Log.d(
                "Timing",
                "Durata della chiamata `module.callAttr`: ${(callEndTime - callStartTime) / 1000.0} s"
            )

            val startTime = System.currentTimeMillis()
            if(PARALLELIZE) {
                val executorService: ExecutorService = Executors.newFixedThreadPool(NTHREADS)
                val frameChunks = framesPyObject.asList().chunked(framesPyObject.asList().size / NTHREADS) // Suddividi in chunk
                val futures = mutableListOf<Future<List<Bitmap>>>()
                for (chunk in frameChunks) {
                    futures.add(executorService.submit(Callable<List<Bitmap>> {
                        chunk.map { byte ->
                            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                            val pixels = IntArray(width * height)
                            val buffer = ByteBuffer.wrap(byte.toJava(ByteArray::class.java))

                            for (i in pixels.indices) {
                                val r = buffer.get().toInt() and 0xFF  // Rosso
                                val g = buffer.get().toInt() and 0xFF  // Verde
                                val b = buffer.get().toInt() and 0xFF  // Blu
                                pixels[i] = (255 shl 24) or (r shl 16) or (g shl 8) or b
                            }
                            bitmap.setPixels(pixels, 0, width, 0, 0, width, height)
                            bitmap
                        }
                    }))
                }

                val combinedFrames = mutableListOf<Bitmap>()
                for (future in futures) {
                    combinedFrames.addAll(future.get()) // Aspetta il risultato di ciascun thread
                }
                frames = combinedFrames // Imposta il risultato finale
                executorService.shutdown() // Ferma il servizio
            } else {
                frames = framesPyObject.asList().map { byte ->
                    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                    val pixels = IntArray(width * height)
                    val buffer = ByteBuffer.wrap(byte.toJava(ByteArray::class.java))

                    for (i in pixels.indices) {
                        val r = buffer.get().toInt() and 0xFF  // Rosso
                        val g = buffer.get().toInt() and 0xFF  // Verde
                        val b = buffer.get().toInt() and 0xFF  // Blu
                        pixels[i] = (255 shl 24) or (r shl 16) or (g shl 8) or b
                    }
                    bitmap.setPixels(pixels, 0, width, 0, 0, width, height)
                    bitmap
                }
            }

            val endTime = System.currentTimeMillis()
            Log.d(
                "Timing",
                "Tempo totale per `handleSpeechResult`: ${(endTime - startTime) / 1000.0} s"
            )

            frameIndex = 0
            progressBar.visibility = View.INVISIBLE
            startFrameAnimation()
        } catch (e: Exception) {
            Toast.makeText(
                this,
                "Errore durante la conversione del testo in frames",
                Toast.LENGTH_SHORT
            ).show()
        }
    }

    private fun startFrameAnimation() {
        handler = Handler(Looper.getMainLooper())
        val runnable = object : Runnable {
            override fun run() {
                frames?.let {
                    if (frameIndex < it.size) {
                        findViewById<ImageView>(R.id.imageView).setImageBitmap(it[frameIndex])
                        frameIndex++
                        handler.postDelayed(this, frameInterval)
                    }
                }
            }
        }
        handler.post(runnable)
        findViewById<ImageView>(R.id.imageView).setImageBitmap(null)
    }



    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer.destroy()
    }

    companion object {
        private const val PARALLELIZE = true
        private const val NTHREADS = 4
    }
}
