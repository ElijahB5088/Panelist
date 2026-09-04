package com.nextpanel.app.data.api

import com.nextpanel.app.BuildConfig
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory

object ApiFactory {
    fun create(): NextPanelApi = Retrofit.Builder()
        .baseUrl(BuildConfig.NEXTPANEL_BASE_URL)
        .addConverterFactory(MoshiConverterFactory.create())
        .build()
        .create(NextPanelApi::class.java)
}