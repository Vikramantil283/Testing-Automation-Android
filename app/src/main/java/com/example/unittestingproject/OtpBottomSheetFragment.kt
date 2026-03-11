package com.example.unittestingproject

import android.content.Intent
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
            view.findViewById<EditText>(R.id.etOtp6)
        )
        val tvOtpError = view.findViewById<TextView>(R.id.tvOtpError)
        val btnVerify  = view.findViewById<Button>(R.id.btnVerifyOtp)

        boxes.forEachIndexed { index, box ->
            box.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    if (s?.length == 1 && index < boxes.lastIndex) {
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
                    boxes[index - 1].apply { requestFocus(); text?.clear() }
                    true
                } else false
            }
        }

        btnVerify.setOnClickListener {
            tvOtpError.visibility = View.GONE
            val otp = boxes.joinToString("") { it.text.toString() }
            when (val result = otpValidator.verify(otp)) {
                is OtpResult.Success -> {
                    val email = arguments?.getString(ARG_EMAIL) ?: ""
                    dismiss()
                    requireActivity().finish()
                    val intent = Intent(requireContext(), DashboardActivity::class.java)
                        .putExtra(DashboardActivity.EXTRA_EMAIL, email)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                    startActivity(intent)
                }
                is OtpResult.Error -> {
                    tvOtpError.text = result.message
                    tvOtpError.visibility = View.VISIBLE
                }
            }
        }

        boxes[0].requestFocus()
    }

    companion object {
        private const val ARG_EMAIL = "arg_email"

        fun newInstance(email: String) = OtpBottomSheetFragment().apply {
            arguments = Bundle().apply { putString(ARG_EMAIL, email) }
        }
    }
}
