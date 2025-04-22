// document.addEventListener('DOMContentLoaded', (event) => {
//     // // Login form submission
//     // const loginForm = document.getElementById('login-form');
//     // if (loginForm) {
//     //     loginForm.addEventListener('submit', async (e) => {
//     //         e.preventDefault();
//     //         const username = document.getElementById('username').value;
//     //         const password = document.getElementById('password').value;
//     //
//     //         try {
//     //             const response = await fetch('/token', {
//     //                 method: 'POST',
//     //                 headers: {
//     //                     'Content-Type': 'application/x-www-form-urlencoded',
//     //                 },
//     //                 body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
//     //             });
//     //
//     //             if (response.ok) {
//     //                 const data = await response.json();
//     //                 localStorage.setItem('token', data.access_token);
//     //                 window.location.href = '/profile';
//     //             } else {
//     //                 alert('Login failed. Please check your credentials.');
//     //             }
//     //         } catch (error) {
//     //             console.error('Error:', error);
//     //         }
//     //     });
//     // }
//
//     // Fetch and display assignment
//     const assignmentContainer = document.getElementById('assignment-container');
//     if (assignmentContainer) {
//         fetchAssignment();
//     }
//
//     // Fetch and display tips
//     const tipsContainer = document.getElementById('tips-container');
//     if (tipsContainer) {
//         fetchTips();
//     }
// });
//
// async function fetchAssignment() {
//     try {
//         const response = await fetch('/users/assignment', {
//             headers: {
//                 'Authorization': `Bearer ${localStorage.getItem('token')}`,
//             },
//         });
//
//         if (response.ok) {
//             const assignment = await response.json();
//             document.getElementById('assignment-container').innerHTML = `
//                 <p>You are assigned to buy a gift for: ${assignment.assigned_user_id}</p>
//             `;
//         } else {
//             document.getElementById('assignment-container').innerHTML = '<p>No assignment found.</p>';
//         }
//     } catch (error) {
//         console.error('Error:', error);
//     }
// }
//
// async function fetchTips() {
//     try {
//         const response = await fetch('/tips/me', {
//             headers: {
//                 'Authorization': `Bearer ${localStorage.getItem('token')}`,
//             },
//         });
//
//         if (response.ok) {
//             const tips = await response.json();
//             const tipsHtml = tips.map(tip => `<li>${tip.content}</li>`).join('');
//             document.getElementById('tips-container').innerHTML = `
//                 <ul>${tipsHtml}</ul>
//             `;
//         } else {
//             document.getElementById('tips-container').innerHTML = '<p>No tips found.</p>';
//         }
//     } catch (error) {
//         console.error('Error:', error);
//     }
// }
