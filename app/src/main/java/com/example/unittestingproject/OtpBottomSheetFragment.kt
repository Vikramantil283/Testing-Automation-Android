package com.example.unittestingproject

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.KeyEvent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import com.google.android.material.bottomsheet.BottomSheetDialogFragment

class OtpBottomSheetFragment : BottomSheetDialogFragment() {

    private val otpValidator = OtpValidator()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View = inflater.inflate(R.layout.fragment_otp_bottom_sheet, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val boxes = listOf(
            view.findViewById<EditText>(R.id.etOtp1),
            view.findViewById(R.id.etOtp2),
            view.findViewById(R.id.etOtp3),
            view.findViewById(R.id.etOtp4),
            view.findViewById(R.id.etOtp5),
            view.findViewById(R.id.etOtp6)
        )
        val tvOtpError = view.findViewById<TextView>(R.id.tvOtpError)
        val btnVerify = view.findViewById<Button>(R.id.btnVerifyOtp)

        // Auto-advance to next box when a digit is entered,
        // move back to previous box on backspace
        boxes.forEachIndexed { index, box ->
            box.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    if (s?.length == 1 && index < boxes.lastIndex) {
                        // Post to next frame so the current key event fully completes
                        // before focus moves — prevents double-typing into the next box
                        boxes[index + 1].post { boxes[index + 1].requestFocus() }
                    }
                }
            })

            box.setOnKeyListener { _, keyCode, event ->
                if (keyCode == KeyEvent.KEYCODE_DEL
                    && event.action == KeyEvent.ACTION_DOWN
                    && box.text.isEmpty()
                    && index > 0
                ) {
                    boxes[index - 1].apply {
                        requestFocus()
                        text?.clear()
                    }
                    true
                } else false
            }
        }

        btnVerify.setOnClickListener {
            tvOtpError.visibility = View.GONE
            val otp = boxes.joinToString("") { it.text.toString() }
            when (val result = otpValidator.verify(otp)) {
                is OtpResult.Success -> {
                    Toast.makeText(
                        requireContext(),
                        "OTP Verified! Login Successful!",
                        Toast.LENGTH_SHORT
                    ).show()
                    dismiss()
                }
                is OtpResult.Error -> {
                    tvOtpError.text = result.message
                    tvOtpError.visibility = View.VISIBLE
                }
            }
        }

        // Focus first box on open
        boxes[0].requestFocus()
    }
}
