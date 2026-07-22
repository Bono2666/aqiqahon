
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** aqiqahon
- **Date:** 2026-07-19
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 Sign in and reach the dashboard
- **Test Code:** [TC001_Sign_in_and_reach_the_dashboard.py](./TC001_Sign_in_and_reach_the_dashboard.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/1162605b-2ee4-4239-a24d-3cc87513704c
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 Keep access to authenticated pages from the dashboard
- **Test Code:** [TC002_Keep_access_to_authenticated_pages_from_the_dashboard.py](./TC002_Keep_access_to_authenticated_pages_from_the_dashboard.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/42779485-be8f-425b-bdaf-a42e7494e693
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 Reject invalid login credentials
- **Test Code:** [TC003_Reject_invalid_login_credentials.py](./TC003_Reject_invalid_login_credentials.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/cada2d4c-5732-4a43-bde5-b1d3529a294e
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 Update a schedule status and driver assignment
- **Test Code:** [TC004_Update_a_schedule_status_and_driver_assignment.py](./TC004_Update_a_schedule_status_and_driver_assignment.py)
- **Test Error:** TEST FAILURE

Saving the schedule did not complete successfully — the updated status/driver could not be verified due to application load errors.

Observations:
- After clicking 'Simpan', the page displayed repeated 'Gagal memuat data jadwal pesanan.' alerts and the DOM is empty.
- No confirmation or updated schedule entry showing status 'Sedang Packing' and driver 'Test Driver' was visible.

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/c9cf3303-0110-48e0-a395-896f47bb8e9a
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 Open a schedule and save updates
- **Test Code:** [TC005_Open_a_schedule_and_save_updates.py](./TC005_Open_a_schedule_and_save_updates.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/860ced98-8c78-4586-bcea-936086e008ae
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 Open today's schedule list and review an order
- **Test Code:** [TC006_Open_todays_schedule_list_and_review_an_order.py](./TC006_Open_todays_schedule_list_and_review_an_order.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/1aa50ca2-4a54-4b18-ab13-8ab7388ade00
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007 View today’s schedule list and find an order
- **Test Code:** [TC007_View_todays_schedule_list_and_find_an_order.py](./TC007_View_todays_schedule_list_and_find_an_order.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/9323cf56-59e7-49a5-a99a-f191b965cb64
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008 Load dashboard counters and notification badge
- **Test Code:** [TC008_Load_dashboard_counters_and_notification_badge.py](./TC008_Load_dashboard_counters_and_notification_badge.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/a8e9de4b-ef99-4bcf-973f-e5eede91f709
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009 Find an order using schedule filters
- **Test Code:** [TC009_Find_an_order_using_schedule_filters.py](./TC009_Find_an_order_using_schedule_filters.py)
- **Test Error:** TEST BLOCKED

The customer filter input ('Pelanggan') could not be located — the test cannot perform the required customer-filtering step.

Observations:
- The page shows many scheduled calendar entries for the customer 'Bono Faradianto' after selecting the status filter.
- The 'Sudah Dijadwalkan' status filter was selected successfully and a page search returned 22 matches for 'Bono Faradianto'.
- Multiple attempts to find or fill a visible 'Pelanggan' text input/control failed and triggered loop-detection; no reliable input with that label was found among the visible interactive elements.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/ff7dc04a-7951-415e-a86e-277d6c8d617d
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010 Filter schedules by operational fields
- **Test Code:** [TC010_Filter_schedules_by_operational_fields.py](./TC010_Filter_schedules_by_operational_fields.py)
- **Test Error:** TEST FAILURE

Customer and driver filter controls are not available on the Jadwal (Schedule) page, so the requested filtering by Customer and Driver cannot be performed.

Observations:
- Only two filter dropdowns are present on the page: 'Semua Cabang' (branch) and 'Semua Status' (status) — these are the only select controls found (visible in the page's interactive elements/shadow DOM).
- No 'Pelanggan' / 'Customer' or 'Pengemudi' / 'Driver' filter controls were found in the UI or interactive element list, preventing selection of those filters.
- The status filter selection succeeded: calendar entries are displayed with titles ending in ' - Sudah Dijadwalkan', confirming the status filter is applied but the customer/driver filters are missing.

Because the UI elements required by the test (Customer and Driver filters) do not exist on the page, the test cannot be completed as specified.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/6e3e60e8-6631-4ee7-8a58-f524b2715a12
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC011 Review all operational order counters on the dashboard
- **Test Code:** [TC011_Review_all_operational_order_counters_on_the_dashboard.py](./TC011_Review_all_operational_order_counters_on_the_dashboard.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/223c6c4e-bb0e-43c9-adac-4368ffcf3733
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC012 Review reminders and open the related schedule
- **Test Code:** [TC012_Review_reminders_and_open_the_related_schedule.py](./TC012_Review_reminders_and_open_the_related_schedule.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/6ab17793-c0a1-409b-816b-7097548da622
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC013 Open overdue reminders from the reminder list
- **Test Code:** [TC013_Open_overdue_reminders_from_the_reminder_list.py](./TC013_Open_overdue_reminders_from_the_reminder_list.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/907a0e96-25b1-44d5-94a6-2d8148916aa8
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC014 View missing driver and incomplete packing reminders
- **Test Code:** [TC014_View_missing_driver_and_incomplete_packing_reminders.py](./TC014_View_missing_driver_and_incomplete_packing_reminders.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/24b566d0-4d1e-460c-9002-9693299928b5
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC015 Add a new goat type and see it in the list
- **Test Code:** [TC015_Add_a_new_goat_type_and_see_it_in_the_list.py](./TC015_Add_a_new_goat_type_and_see_it_in_the_list.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/70b515ea-8eb7-4e09-b8a6-c50ae5130303/8505cf46-9c26-46f6-9eeb-c8b70f0c2a64
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **80.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---