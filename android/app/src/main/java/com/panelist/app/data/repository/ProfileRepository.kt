package com.panelist.app.data.repository

import com.panelist.app.data.api.PanelistApi
import com.panelist.app.data.model.FloppyConfig
import com.panelist.app.data.model.FloppyConnectionResponse
import com.panelist.app.data.model.ProfileResponse
import com.panelist.app.data.model.SyncStatus

class ProfileRepository(private val api: PanelistApi) {
    suspend fun profile(): ProfileResponse = api.profile()
    suspend fun test(config: FloppyConfig): FloppyConnectionResponse = api.testFloppy(config)
    suspend fun connect(config: FloppyConfig): Boolean = api.connectFloppy(config).connected
    suspend fun sync(): Boolean = api.sync().ok
    suspend fun syncStatus(): SyncStatus = api.syncStatus()
}