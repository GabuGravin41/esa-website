/**
 * Dynamic Event Calendar for ESA-KU Website
 * This script creates a responsive event calendar that displays events
 * and allows interaction with those events.
 */

class EventCalendar {
    constructor(containerSelector, options = {}) {
        this.container = document.querySelector(containerSelector);
        if (!this.container) {
            console.error('Calendar container not found:', containerSelector);
            return;
        }
        
        this.options = {
            eventsUrl: options.eventsUrl || '/api/events/',
            monthFormat: options.monthFormat || { month: 'long', year: 'numeric' },
            dayFormat: options.dayFormat || { day: 'numeric' },
            firstDayOfWeek: options.firstDayOfWeek || 1, // Monday
            ...options
        };
        
        this.currentDate = new Date();
        this.events = [];
        
        this.init();
    }
    
    init() {
        this.fetchEvents().then(() => {
            this.render();
            this.attachEventListeners();
        });
    }
    
    async fetchEvents() {
        try {
            // Get year and month for filtering events
            const year = this.currentDate.getFullYear();
            const month = this.currentDate.getMonth() + 1; // JavaScript months are 0-indexed
            
            const response = await fetch(`${this.options.eventsUrl}?year=${year}&month=${month}`);
            if (!response.ok) {
                throw new Error('Failed to fetch events');
            }
            
            this.events = await response.json();
            
            // Parse dates
            this.events.forEach(event => {
                event.startDate = new Date(event.start_date);
                event.endDate = event.end_date ? new Date(event.end_date) : null;
            });
            
        } catch (error) {
            console.error('Error fetching events:', error);
            this.events = [];
        }
    }
    
    render() {
        const calendarHtml = this.generateCalendarHtml();
        this.container.innerHTML = calendarHtml;
        this.populateEvents();
    }
    
    generateCalendarHtml() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        
        // Get the first day of the month
        const firstDayOfMonth = new Date(year, month, 1);
        
        // Get the last day of the month
        const lastDayOfMonth = new Date(year, month + 1, 0);
        
        // Get the day of the week the first day falls on (0 = Sunday, 1 = Monday, etc.)
        let firstDayOfWeek = firstDayOfMonth.getDay();
        
        // Adjust for the first day of the week setting
        firstDayOfWeek = (firstDayOfWeek - this.options.firstDayOfWeek + 7) % 7;
        
        // Month and year header
        const monthYearHeader = new Intl.DateTimeFormat('en-US', this.options.monthFormat).format(firstDayOfMonth);
        
        // Days of the week header
        const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        // Reorder based on firstDayOfWeek
        const orderedDaysOfWeek = [
            ...daysOfWeek.slice(this.options.firstDayOfWeek % 7),
            ...daysOfWeek.slice(0, this.options.firstDayOfWeek % 7)
        ];
        
        let html = `
        <div class="event-calendar">
            <div class="calendar-header">
                <button class="prev-month" aria-label="Previous month">&lt;</button>
                <h3 class="month-year">${monthYearHeader}</h3>
                <button class="next-month" aria-label="Next month">&gt;</button>
            </div>
            <div class="calendar-grid">
                <div class="days-header">
        `;
        
        // Add day headers
        orderedDaysOfWeek.forEach(day => {
            html += `<div class="day-name">${day.substring(0, 3)}</div>`;
        });
        
        html += `
                </div>
                <div class="days-grid">
        `;
        
        // Calculate total number of cells needed (previous month days + current month days + next month days)
        const totalDays = firstDayOfWeek + lastDayOfMonth.getDate();
        const totalRows = Math.ceil(totalDays / 7);
        const totalCells = totalRows * 7;
        
        // Days from previous month
        const prevMonthDays = firstDayOfWeek;
        const prevMonthLastDay = new Date(year, month, 0).getDate();
        
        for (let i = 0; i < prevMonthDays; i++) {
            const dayNum = prevMonthLastDay - prevMonthDays + i + 1;
            html += `<div class="day other-month" data-date="${year}-${month === 0 ? 12 : month}-${dayNum}">
                        <span class="day-number">${dayNum}</span>
                        <div class="day-events"></div>
                    </div>`;
        }
        
        // Days from current month
        for (let i = 1; i <= lastDayOfMonth.getDate(); i++) {
            const isToday = new Date(year, month, i).toDateString() === new Date().toDateString();
            const dateAttr = `${year}-${(month + 1).toString().padStart(2, '0')}-${i.toString().padStart(2, '0')}`;
            
            html += `<div class="day${isToday ? ' today' : ''}" data-date="${dateAttr}">
                        <span class="day-number">${i}</span>
                        <div class="day-events"></div>
                    </div>`;
        }
        
        // Days from next month
        const nextMonthDays = totalCells - (prevMonthDays + lastDayOfMonth.getDate());
        for (let i = 1; i <= nextMonthDays; i++) {
            html += `<div class="day other-month" data-date="${year}-${month === 11 ? 1 : month + 2}-${i}">
                        <span class="day-number">${i}</span>
                        <div class="day-events"></div>
                    </div>`;
        }
        
        html += `
                </div>
            </div>
        </div>
        `;
        
        return html;
    }
    
    populateEvents() {
        // Group events by day
        const eventsByDay = {};
        
        this.events.forEach(event => {
            // For multi-day events, we need to add the event to each day it spans
            let currentDate = new Date(event.startDate);
            const endDate = event.endDate || currentDate;
            
            while (currentDate <= endDate) {
                const dateKey = currentDate.toISOString().split('T')[0]; // YYYY-MM-DD
                
                if (!eventsByDay[dateKey]) {
                    eventsByDay[dateKey] = [];
                }
                
                eventsByDay[dateKey].push(event);
                
                // Move to next day
                currentDate = new Date(currentDate);
                currentDate.setDate(currentDate.getDate() + 1);
            }
        });
        
        // Add events to the calendar
        Object.entries(eventsByDay).forEach(([dateKey, dayEvents]) => {
            const dayCell = this.container.querySelector(`.day[data-date="${dateKey}"]`);
            if (!dayCell) return;
            
            const eventsContainer = dayCell.querySelector('.day-events');
            
            if (dayEvents.length === 1) {
                // Single event
                const event = dayEvents[0];
                eventsContainer.innerHTML = `
                    <div class="event" data-event-id="${event.id}" style="background-color: ${this.getCategoryColor(event.category)}">
                        <span class="event-title">${event.title}</span>
                    </div>
                `;
            } else if (dayEvents.length > 1) {
                // Multiple events
                eventsContainer.innerHTML = `
                    <div class="multiple-events" data-count="${dayEvents.length}">
                        <span>${dayEvents.length} Events</span>
                    </div>
                    <div class="events-tooltip">
                        <div class="tooltip-content">
                            <h4>${dayEvents.length} Events on ${new Date(dateKey).toLocaleDateString()}</h4>
                            <ul>
                                ${dayEvents.map(event => `
                                    <li>
                                        <a href="/events/${event.id}/" class="event-link" data-event-id="${event.id}">
                                            <span class="event-time">${this.formatTime(event.startDate)}</span>
                                            <span class="event-title">${event.title}</span>
                                        </a>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>
                `;
            }
        });
    }
    
    attachEventListeners() {
        // Previous month button
        const prevButton = this.container.querySelector('.prev-month');
        if (prevButton) {
            prevButton.addEventListener('click', () => {
                this.currentDate.setMonth(this.currentDate.getMonth() - 1);
                this.fetchEvents().then(() => {
                    this.render();
                    this.attachEventListeners();
                });
            });
        }
        
        // Next month button
        const nextButton = this.container.querySelector('.next-month');
        if (nextButton) {
            nextButton.addEventListener('click', () => {
                this.currentDate.setMonth(this.currentDate.getMonth() + 1);
                this.fetchEvents().then(() => {
                    this.render();
                    this.attachEventListeners();
                });
            });
        }
        
        // Single event click
        const eventElements = this.container.querySelectorAll('.event');
        eventElements.forEach(element => {
            element.addEventListener('click', () => {
                const eventId = element.dataset.eventId;
                window.location.href = `/events/${eventId}/`;
            });
        });
        
        // Multiple events hover
        const multipleEvents = this.container.querySelectorAll('.multiple-events');
        multipleEvents.forEach(element => {
            const tooltip = element.parentElement.querySelector('.events-tooltip');
            
            element.addEventListener('mouseenter', () => {
                tooltip.classList.add('visible');
            });
            
            element.addEventListener('mouseleave', () => {
                tooltip.classList.remove('visible');
            });
        });
        
        // Event link clicks in tooltip
        const eventLinks = this.container.querySelectorAll('.event-link');
        eventLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const eventId = link.dataset.eventId;
                window.location.href = `/events/${eventId}/`;
            });
        });
    }
    
    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    getCategoryColor(category) {
        const colors = {
            'workshop': '#4285F4', // Blue
            'seminar': '#0F9D58', // Green
            'conference': '#DB4437', // Red
            'networking': '#F4B400', // Yellow
            'competition': '#9C27B0', // Purple
            'other': '#795548', // Brown
        };
        
        return colors[category] || '#607D8B'; // Default gray
    }
}

// Initialize the calendar when the DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const calendar = new EventCalendar('#event-calendar', {
        eventsUrl: '/api/events/'
    });
});
